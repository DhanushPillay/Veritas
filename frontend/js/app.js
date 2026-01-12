/**
 * VERITAS - Main Application
 * Media Verification System
 */

const App = {
  // State
  activeTab: 'ai-detect',
  inputText: '',
  selectedFile: null,
  status: 'IDLE', // IDLE, ANALYZING, COMPLETED, ERROR
  result: null,
  useSearch: false,
  cooldown: 0,
  currentThumbnail: null,
  analysisSteps: [],
  learningRules: [],
  history: [],

  // Constants
  RATE_LIMIT_SECONDS: 10,

  // Initialize the app
  init() {
    // Load from localStorage
    this.learningRules = JSON.parse(localStorage.getItem('veritas_learning_rules') || '[]');
    this.history = JSON.parse(localStorage.getItem('veritas_history') || '[]');

    // Check API key
    if (!GeminiService.hasApiKey()) {
      this.showApiKeyModal();
    } else {
      this.render();
    }

    // Event listeners
    this.setupEventListeners();
  },

  setupEventListeners() {
    // Clipboard paste handler
    window.addEventListener('paste', (e) => {
      if (this.status !== 'IDLE' || this.activeTab === 'text') return;

      if (e.clipboardData && e.clipboardData.files.length > 0) {
        const file = e.clipboardData.files[0];
        const validTypes = {
          image: file.type.startsWith('image/'),
          video: file.type.startsWith('video/'),
          audio: file.type.startsWith('audio/')
        };

        if (validTypes[this.activeTab]) {
          e.preventDefault();
          this.selectedFile = file;
          this.render();
        }
      }
    });
  },

  // Show API key modal
  showApiKeyModal() {
    document.getElementById('app').innerHTML = `
      <div class="modal-overlay">
        <div class="modal">
          <div class="modal-icon">${Icons.shieldCheck()}</div>
          <h2>API Key Required</h2>
          <p>Veritas uses Gemini 2.0 Flash for multimodal media forensics. Enter your API key to continue.</p>
          <input type="password" class="modal-input" id="apiKeyInput" placeholder="Enter your Gemini API key">
          <div class="modal-info">
            <p><strong>Note:</strong> Get a free API key from Google AI Studio.</p>
            <a href="https://aistudio.google.com/app/apikey" target="_blank">Get Free API Key →</a>
          </div>
          <button class="btn-primary" onclick="App.saveApiKey()">Connect API Key</button>
        </div>
      </div>`;
  },

  // Save API key and proceed
  saveApiKey() {
    const key = document.getElementById('apiKeyInput').value.trim();
    if (key) {
      GeminiService.setApiKey(key);
      this.render();
    }
  },

  // Main render function
  render() {
    const app = document.getElementById('app');

    switch (this.status) {
      case 'IDLE':
        app.innerHTML = this.renderNavbar() + this.renderMainContent() + '</main>';
        break;
      case 'ANALYZING':
        app.innerHTML = this.renderNavbar() + this.renderAnalyzing() + '</main>';
        break;
      case 'COMPLETED':
        app.innerHTML = this.renderNavbar() + '<main class="main-container">' +
          ResultView.render(this.result, this.currentThumbnail, this.activeTab) + '</main>';
        break;
      case 'ERROR':
        app.innerHTML = this.renderNavbar() + this.renderError() + '</main>';
        break;
    }
  },

  // Render navbar
  renderNavbar() {
    return `
      <nav class="navbar">
        <div class="navbar-content">
          <div class="navbar-brand">
            ${Icons.shieldCheck()}
            <span>VERITAS</span>
          </div>
          <div class="status-badge">
            <span class="dot"></span>
            System Operational
          </div>
        </div>
      </nav>`;
  },

  // Render main content (IDLE state)
  renderMainContent() {
    return `
      <main class="main-container">
        <div class="hero">
          <h1>Verify Reality in Real-Time</h1>
          <p>Advanced AI forensics to detect deepfakes, synthetic voices, and generated text with precision.</p>
        </div>
        
        ${this.renderTabs()}
        ${this.renderInputCard()}
        ${this.history.length > 0 ? this.renderHistory() : ''}
      </main>`;
  },

  // Render tab buttons
  renderTabs() {
    const tabs = [
      { id: 'ai-detect', label: 'AI Detection', icon: Icons.activity() },
      { id: 'fact-check', label: 'Fact Check', icon: Icons.fileText() },
      { id: 'image', label: 'Image Analysis', icon: Icons.image() },
      { id: 'audio', label: 'Voice/Audio', icon: Icons.mic() },
      { id: 'video', label: 'Video Forensics', icon: Icons.video() }
    ];

    return `
      <div class="tabs">
        ${tabs.map(t => `
          <button class="tab-btn ${this.activeTab === t.id ? 'active' : ''}" 
                  onclick="App.setTab('${t.id}')">
            ${t.icon}
            <span>${t.label}</span>
          </button>
        `).join('')}
      </div>`;
  },

  // Set active tab
  setTab(tab) {
    this.activeTab = tab;
    this.selectedFile = null;
    this.render();
  },

  // Render input card
  renderInputCard() {
    const fileText = this.selectedFile ? this.selectedFile.name : `Drop your ${this.activeTab} file here`;
    const isTextTab = this.activeTab === 'ai-detect' || this.activeTab === 'fact-check';

    // Different placeholders for each text mode
    const placeholders = {
      'ai-detect': 'Paste text to check if it was written by AI or a human...',
      'fact-check': 'Paste a claim, article, or statement to verify its accuracy...'
    };
    const inputLabels = {
      'ai-detect': 'Text to Analyze for AI Detection',
      'fact-check': 'Claim or Statement to Fact-Check'
    };

    return `
      <div class="input-card">
        ${isTextTab ? `
          <label class="input-label">${inputLabels[this.activeTab] || 'Content to Analyze'}</label>
          <textarea class="text-input" id="textInput" 
                    placeholder="${placeholders[this.activeTab] || 'Paste text here...'}"
                    oninput="App.inputText = this.value">${this.inputText}</textarea>
          ${this.activeTab === 'ai-detect' ? `
            <p class="input-hint">🧠 Uses your trained ML model to detect AI-generated text patterns.</p>
          ` : `
            <p class="input-hint">🔍 Searches the web and uses AI to verify claims and find sources.</p>
          `}
        ` : `
          <label class="input-label">Upload Media Evidence</label>
          <div class="upload-area ${this.selectedFile ? 'has-file' : ''}">
            <input type="file" accept="${this.getAcceptTypes()}" onchange="App.handleFileSelect(event)">
            <div class="upload-icon">${Icons.upload()}</div>
            <p class="upload-text">${fileText}</p>
            <p class="upload-hint">or click to browse or paste (Ctrl+V)</p>
          </div>
        `}
        
        <div class="controls-row">
          ${this.activeTab === 'fact-check' ? `
            <div class="toggle-wrapper" onclick="App.toggleSearch()">
              <div class="toggle ${this.useSearch ? 'active' : ''}">
                <div class="toggle-knob"></div>
              </div>
              <span class="toggle-label">Web Search Provenance</span>
            </div>
          ` : '<div></div>'}
          
          <div style="display: flex; align-items: center; gap: 1rem;">
            <p class="privacy-note">*Veritas processes data privately. Max 2GB.</p>
            <button class="btn-analyze" onclick="App.runAnalysis()" 
                    ${this.isInputEmpty() || this.cooldown > 0 ? 'disabled' : ''}>
              ${this.cooldown > 0
        ? `<span>Wait ${this.cooldown}s</span>`
        : `${Icons.activity()} ${this.activeTab === 'ai-detect' ? 'Detect AI' : 'Run Analysis'}`}
            </button>
          </div>
        </div>
      </div>`;
  },

  // Get file accept types
  getAcceptTypes() {
    const types = { audio: 'audio/*', video: 'video/*', image: 'image/*' };
    return types[this.activeTab] || '*';
  },

  // Check if input is empty
  isInputEmpty() {
    const isTextTab = this.activeTab === 'ai-detect' || this.activeTab === 'fact-check';
    return isTextTab ? !this.inputText : !this.selectedFile;
  },

  // Handle file selection
  handleFileSelect(event) {
    if (event.target.files && event.target.files[0]) {
      this.selectedFile = event.target.files[0];
      this.render();
    }
  },

  // Toggle search option
  toggleSearch() {
    this.useSearch = !this.useSearch;
    this.render();
  },

  // Render history section
  renderHistory() {
    return `
      <div class="history-section">
        <div class="history-header">
          <h3 class="history-title">Recent Analysis</h3>
          <button class="btn-clear-history" onclick="App.clearHistory()">
            ${Icons.trash()}
            Clear History
          </button>
        </div>
        <div class="history-grid">
          ${this.history.map(item => this.renderHistoryItem(item)).join('')}
        </div>
      </div>`;
  },

  // Render single history item
  renderHistoryItem(item) {
    const isAuthentic = item.result.verdict === 'Authentic';
    const isSuspicious = item.result.verdict === 'Fake/Generated' || item.result.verdict === 'Suspicious';
    const verdictClass = isAuthentic ? 'authentic' : isSuspicious ? 'suspicious' : 'inconclusive';

    return `
      <div class="history-item" onclick="App.loadHistoryItem('${item.id}')">
        <div class="history-thumb">
          ${item.mediaThumbnail
        ? `<img src="${item.mediaThumbnail}" alt="preview">`
        : Icons.getMediaTypeIcon(item.type)}
        </div>
        <div class="history-content">
          <div class="history-meta">
            <span class="history-date">${new Date(item.timestamp).toLocaleDateString()}</span>
            <span class="history-verdict ${verdictClass}">${item.result.verdict}</span>
          </div>
          <p class="history-preview">${item.preview}</p>
        </div>
      </div>`;
  },

  // Load history item
  loadHistoryItem(id) {
    const item = this.history.find(h => h.id === id);
    if (item) {
      this.result = item.result;
      this.activeTab = item.type;
      this.currentThumbnail = item.mediaThumbnail;
      this.status = 'COMPLETED';
      this.render();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  },

  // Clear history
  clearHistory() {
    if (confirm('Are you sure you want to clear your verification history?')) {
      this.history = [];
      localStorage.setItem('veritas_history', '[]');
      this.render();
    }
  },

  // Get analysis steps
  getAnalysisSteps(type, search) {
    const steps = ['Initializing forensic protocols...'];

    const typeSteps = {
      text: ['Analyzing linguistic patterns...', 'Checking logical consistency...', 'Detecting LLM generation markers...'],
      image: ['Scanning Exif & metadata...', 'Analyzing Error Level Analysis...', 'Checking shadow coherence...', 'Scanning for AI artifacts...'],
      audio: ['Generating spectral analysis...', 'Detecting voice cloning...', 'Analyzing breathing patterns...'],
      video: ['Extracting keyframes...', 'Checking audio-visual sync...', 'Analyzing temporal consistency...', 'Detecting face manipulation...']
    };

    steps.push(...(typeSteps[type] || []));

    if (search) {
      steps.push('Connecting to global index...', 'Cross-referencing sources...');
    } else {
      steps.push('Skipping external search (Local Analysis)...');
    }

    if (this.learningRules.length > 0) {
      steps.push('Applying user-taught protocols...');
    }

    steps.push('Compiling final forensic verdict...');
    return steps;
  },

  // Run analysis
  async runAnalysis() {
    if (this.cooldown > 0 || this.isInputEmpty()) return;

    // Start cooldown
    this.cooldown = this.RATE_LIMIT_SECONDS;
    this.startCooldownTimer();

    // Set analyzing state
    this.status = 'ANALYZING';

    // Initialize steps
    const stepLabels = this.getAnalysisSteps(this.activeTab, this.useSearch);
    this.analysisSteps = stepLabels.map((label, idx) => ({
      id: idx,
      label,
      status: idx === 0 ? 'processing' : 'pending'
    }));

    this.render();

    // Animate steps
    let currentStep = 0;
    const stepInterval = setInterval(() => {
      if (currentStep >= this.analysisSteps.length - 1) return;

      this.analysisSteps[currentStep].status = 'completed';
      currentStep++;
      this.analysisSteps[currentStep].status = 'processing';
      this.updateAnalysisSteps();
    }, 1500);

    try {
      // Generate thumbnail
      if (this.selectedFile) {
        this.currentThumbnail = await this.generateThumbnail(this.selectedFile, this.activeTab);
      } else {
        this.currentThumbnail = null;
      }

      // Call API
      const content = this.activeTab === 'text' ? this.inputText : this.selectedFile;
      const result = await GeminiService.verifyMedia(this.activeTab, content, this.useSearch, this.learningRules);

      // Save to history
      const newItem = {
        id: crypto.randomUUID(),
        timestamp: Date.now(),
        type: this.activeTab,
        preview: this.activeTab === 'text'
          ? (this.inputText.length > 60 ? this.inputText.substring(0, 60) + '...' : this.inputText)
          : (this.selectedFile?.name || 'Unknown File'),
        mediaThumbnail: this.currentThumbnail,
        result
      };

      this.history.unshift(newItem);
      localStorage.setItem('veritas_history', JSON.stringify(this.history));

      this.result = result;
      this.status = 'COMPLETED';
    } catch (error) {
      console.error('Analysis failed:', error);
      if (error.message?.includes('API key')) {
        GeminiService.setApiKey('');
      }
      this.status = 'ERROR';
    } finally {
      clearInterval(stepInterval);
      this.render();
    }
  },

  // Start cooldown timer
  startCooldownTimer() {
    const timer = setInterval(() => {
      this.cooldown--;
      if (this.cooldown <= 0) {
        clearInterval(timer);
        if (this.status === 'IDLE') this.render();
      }
    }, 1000);
  },

  // Update analysis steps display
  updateAnalysisSteps() {
    const container = document.getElementById('analysisSteps');
    if (container) {
      container.innerHTML = this.analysisSteps.map(step => `
        <div class="step">
          <div class="step-indicator ${step.status}">
            ${step.status === 'completed' ? Icons.check() : ''}
          </div>
          <span class="step-label ${step.status}">${step.label}</span>
        </div>
      `).join('');
    }
  },

  // Render analyzing state
  renderAnalyzing() {
    return `
      <main class="main-container">
        <div class="analyzing-container">
          <div class="spinner-wrapper">
            <div class="spinner"></div>
            <div class="spinner-icon">${Icons.shieldCheck()}</div>
          </div>
          <h2 class="analyzing-title">Analyzing Integrity</h2>
          <div class="analysis-steps" id="analysisSteps">
            ${this.analysisSteps.map(step => `
              <div class="step">
                <div class="step-indicator ${step.status}">
                  ${step.status === 'completed' ? Icons.check() : ''}
                </div>
                <span class="step-label ${step.status}">${step.label}</span>
              </div>
            `).join('')}
          </div>
        </div>
      </main>`;
  },

  // Render error state
  renderError() {
    return `
      <main class="main-container">
        <div class="error-container">
          <div class="error-icon">${Icons.activity()}</div>
          <h2>Analysis Failed</h2>
          <p>We encountered an issue processing your request. Please ensure you are using a valid API key.</p>
          <div class="error-buttons">
            <button class="btn-error-home" onclick="App.resetAnalysis()">Return Home</button>
            <button class="btn-error-key" onclick="App.showApiKeyModal()">Update API Key</button>
          </div>
        </div>
      </main>`;
  },

  // Reset analysis
  resetAnalysis() {
    this.status = 'IDLE';
    this.result = null;
    this.inputText = '';
    this.selectedFile = null;
    this.analysisSteps = [];
    this.currentThumbnail = null;
    this.render();
  },

  // Add learning rule
  addLearningRule(rule) {
    this.learningRules.push(rule);
    localStorage.setItem('veritas_learning_rules', JSON.stringify(this.learningRules));
  },

  // Generate thumbnail for media
  async generateThumbnail(file, type) {
    if (type === 'text') return null;

    try {
      if (type === 'image') {
        return await this.thumbnailFromImage(file);
      } else if (type === 'video') {
        return await this.thumbnailFromVideo(file);
      } else if (type === 'audio') {
        return this.generateAudioWaveform();
      }
    } catch (e) {
      console.error('Thumbnail generation failed:', e);
      return null;
    }
  },

  // Generate thumbnail from image
  thumbnailFromImage(file) {
    return new Promise(resolve => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d');
          const maxSize = 300;
          let { width, height } = img;

          if (width > height && width > maxSize) {
            height *= maxSize / width;
            width = maxSize;
          } else if (height > maxSize) {
            width *= maxSize / height;
            height = maxSize;
          }

          canvas.width = width;
          canvas.height = height;
          ctx.drawImage(img, 0, 0, width, height);
          resolve(canvas.toDataURL('image/jpeg', 0.6));
        };
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);
    });
  },

  // Generate thumbnail from video
  thumbnailFromVideo(file) {
    return new Promise(resolve => {
      const video = document.createElement('video');
      video.preload = 'metadata';
      video.src = URL.createObjectURL(file);
      video.muted = true;
      video.currentTime = 0.5;

      video.onseeked = () => {
        const canvas = document.createElement('canvas');
        const maxSize = 300;
        let { videoWidth: width, videoHeight: height } = video;

        if (width > height && width > maxSize) {
          height *= maxSize / width;
          width = maxSize;
        } else if (height > maxSize) {
          width *= maxSize / height;
          height = maxSize;
        }

        canvas.width = width;
        canvas.height = height;
        canvas.getContext('2d').drawImage(video, 0, 0, width, height);
        URL.revokeObjectURL(video.src);
        resolve(canvas.toDataURL('image/jpeg', 0.6));
      };

      setTimeout(() => resolve(null), 3000);
    });
  },

  // Generate audio waveform visual
  generateAudioWaveform() {
    const canvas = document.createElement('canvas');
    canvas.width = 300;
    canvas.height = 80;
    const ctx = canvas.getContext('2d');

    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, 300, 80);

    ctx.fillStyle = '#38bdf8';
    const barWidth = 4, gap = 2;
    const bars = Math.floor(300 / (barWidth + gap));

    for (let i = 0; i < bars; i++) {
      const h = Math.random() * 50 + 10;
      const x = i * (barWidth + gap);
      const y = (80 - h) / 2;
      ctx.fillRect(x, y, barWidth, h);
    }

    return canvas.toDataURL('image/png');
  }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => App.init());
