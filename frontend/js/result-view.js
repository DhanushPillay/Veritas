const ResultView = {
  currentResult: null,
  mediaThumbnail: null,
  mediaType: null,
  expandedDetails: new Set(),
  isReporting: false,
  localVerdict: null,

  // Render the complete results view
  render(result, thumbnail, type) {
    this.currentResult = result;
    this.mediaThumbnail = thumbnail;
    this.mediaType = type;
    this.localVerdict = result.verdict;

    const isAuthentic = result.verdict === 'Authentic';
    const isSuspicious = result.verdict === 'AI-Generated' || result.verdict === 'Suspicious';
    const isInconclusive = result.verdict === 'Inconclusive';

    // Auto-expand details if suspicious
    this.expandedDetails = isSuspicious
      ? new Set(result.technicalDetails.map((_, i) => i))
      : new Set();

    const verdictClass = isAuthentic ? 'authentic' : isSuspicious ? 'suspicious' : 'inconclusive';
    const gaugeColor = isAuthentic ? '#10b981' : isSuspicious ? '#ef4444' : '#f59e0b';

    let html = '<div class="results-container">';

    // Evidence Preview
    if (thumbnail && type !== 'text') {
      html += `
        <div class="evidence-preview">
          <div class="evidence-badge">
            ${Icons.getMediaTypeIcon(type)}
            <span>${type.toUpperCase()} Evidence</span>
          </div>
          <img src="${thumbnail}" alt="Evidence Preview" class="evidence-image">
        </div>`;
    }

    // Verdict Banner
    html += `
      <div class="verdict-banner ${verdictClass}">
        <div class="verdict-info">
          <div class="verdict-icon">
            ${isAuthentic ? Icons.shieldCheck() : Icons.alertTriangle()}
          </div>
          <div>
            <h2 class="verdict-label">Analysis Verdict</h2>
            <h1 class="verdict-text">${result.verdict}</h1>
          </div>
        </div>
        <div class="confidence-gauge">
          <div class="gauge-circle" style="--confidence: ${result.confidence}; --gauge-color: ${gaugeColor}">
            <div class="gauge-inner">
              <span class="gauge-value">${result.confidence}%</span>
              <span class="gauge-label">Trust</span>
            </div>
          </div>
        </div>
      </div>`;

    // Inconclusive Warning
    if (isInconclusive) {
      html += `
        <div class="inconclusive-warning">
          ${Icons.alertTriangle()}
          <div>
            <h4>Manual Review Recommended</h4>
            <p>The system could not definitively verify this media. Low resolution, compression, or ambiguous features may have affected analysis.</p>
          </div>
        </div>`;
    }

    // Analysis Type Badge (shows what type of analysis was performed)
    if (result.analysisType) {
      const typeLabels = {
        'fact_check': { icon: '🔍', label: 'Fact Check', color: '#3b82f6' },
        'ai_detection': { icon: '🤖', label: 'AI Detection', color: '#8b5cf6' },
        'both': { icon: '⚡', label: 'Full Analysis', color: '#10b981' }
      };
      const typeInfo = typeLabels[result.analysisType.primary] || typeLabels.both;

      html += `
        <div class="analysis-type-section">
          <div class="analysis-type-badge" style="--badge-color: ${typeInfo.color}">
            <span class="type-icon">${typeInfo.icon}</span>
            <span class="type-label">${typeInfo.label}</span>
          </div>
          <p class="type-reason">${result.analysisType.reason}</p>
          ${result.analysisType.indicators?.length ? `
            <div class="type-indicators">
              ${result.analysisType.indicators.map(i => `<span class="indicator-chip">${i}</span>`).join('')}
            </div>
          ` : ''}
        </div>`;
    }

    // AI Text Detection Results (prominent display for text type)
    if (type === 'text' && result.aiTextDetection) {
      const aiResult = result.aiTextDetection;
      const isAI = aiResult.is_ai;
      const confidence = aiResult.confidence;
      const aiColor = isAI ? '#ef4444' : '#10b981';
      const aiLabel = isAI ? '🤖 AI-Generated Text' : '👤 Human-Written Text';

      html += `
        <div class="ai-detection-card ${isAI ? 'ai-detected' : 'human-detected'}">
          <div class="ai-detection-header">
            <h3>${aiLabel}</h3>
            <div class="ai-confidence" style="--ai-color: ${aiColor}">
              <span class="ai-conf-value">${confidence.toFixed(1)}%</span>
              <span class="ai-conf-label">ML Confidence</span>
            </div>
          </div>
          <div class="ai-detection-bar">
            <div class="ai-bar-label">Human</div>
            <div class="ai-bar-container">
              <div class="ai-bar-human" style="width: ${aiResult.probabilities?.human || 0}%"></div>
              <div class="ai-bar-ai" style="width: ${aiResult.probabilities?.ai_generated || 0}%"></div>
            </div>
            <div class="ai-bar-label">AI</div>
          </div>
          <p class="ai-detection-note">
            ${isAI
          ? '⚠️ This text shows patterns consistent with AI-generated content.'
          : '✅ This text appears to be written by a human.'}
          </p>
        </div>`;
    }

    // Results Grid
    html += '<div class="results-grid">';

    // Left Column - Findings
    html += `
      <div class="findings-column">
        <section class="section-card">
          <h3 class="section-title">Executive Summary</h3>
          <p class="summary-text">${result.summary}</p>
        </section>
        <section class="section-card" style="margin-top: 1.5rem;">
          <h3 class="section-title">Key Findings</h3>
          <ul class="findings-list">
            ${result.reasoning.map(r => `<li>${r}</li>`).join('')}
          </ul>
        </section>
        ${this.renderRiskScore(result)}
        ${this.renderReverseSearch(result)}
      </div>`;

    // Right Column - Technical Details
    html += `
      <div class="tech-column">
        <section class="section-card">
          <h3 class="section-title">Technical Analysis</h3>
          <div id="techDetails">
            ${this.renderTechDetails(result.technicalDetails)}
          </div>
        </section>`;

    // Sources
    if (result.sources && result.sources.length > 0) {
      html += `
        <section class="section-card" style="margin-top: 1rem;">
          <h3 class="section-title">Verified Sources</h3>
          <ul class="sources-list">
            ${result.sources.map(s => `<li><a href="${s.uri}" target="_blank">${s.title || s.uri}</a></li>`).join('')}
          </ul>
        </section>`;
    }

    html += `
        <button class="btn-secondary" onclick="App.resetAnalysis()">Start New Analysis</button>
      </div>`;

    html += '</div>'; // End results-grid

    // Feedback Section
    html += `
      <div class="feedback-section" id="feedbackSection">
        <button class="btn-report" onclick="ResultView.showFeedbackForm()">
          ${Icons.alertTriangle()}
          Report Incorrect Verdict
        </button>
      </div>`;

    html += '</div>'; // End results-container

    return html;
  },

  // Render risk score bar (for images)
  renderRiskScore(result) {
    const risk = result.riskScore;
    if (risk === undefined) return '';

    const level = risk > 70 ? 'high' : risk > 40 ? 'medium' : 'low';
    const label = risk > 70 ? 'HIGH RISK' : risk > 40 ? 'MODERATE' : 'LOW RISK';
    const color = risk > 70 ? '#ef4444' : risk > 40 ? '#f59e0b' : '#10b981';

    return `
      <section class="section-card" style="margin-top: 1.5rem;">
        <h3 class="section-title">Misinformation Risk Score</h3>
        <div class="risk-container">
          <div class="risk-bar-bg">
            <div class="risk-bar-fill" style="width: ${risk}%; background: ${color}"></div>
          </div>
          <div class="risk-info">
            <span class="risk-value" style="color: ${color}">${risk}%</span>
            <span class="risk-label ${level}">${label}</span>
          </div>
        </div>
        ${result.forensics ? `
          <div class="risk-details">
            ${result.forensics.manipulation_indicators?.map(i =>
      `<div class="indicator ${i.severity}">• ${i.description}</div>`
    ).join('') || ''}
          </div>
        ` : ''}
      </section>`;
  },

  // Render reverse image search results
  renderReverseSearch(result) {
    const reverse = result.reverseSearch;
    if (!reverse) return '';

    return `
      <section class="section-card" style="margin-top: 1.5rem;">
        <h3 class="section-title">Reverse Image Search</h3>
        <div class="reverse-search-info">
          <div class="matches-count">
            <span class="count">${reverse.matches || 0}</span>
            <span class="label">matches found online</span>
          </div>
          ${reverse.originality_score ? `
            <div class="originality">
              Originality: <strong>${reverse.originality_score}%</strong>
            </div>
          ` : ''}
        </div>
        <div class="search-links">
          <span class="search-label">Search manually:</span>
          ${reverse.manual_urls ? Object.entries(reverse.manual_urls).map(([name, url]) =>
      `<a href="${url}" target="_blank" class="search-link">${name}</a>`
    ).join(' ') : ''}
        </div>
      </section>`;
  },

  // Render technical details with expandable sections
  renderTechDetails(details) {
    return details.map((item, idx) => {
      const isExpanded = this.expandedDetails.has(idx);
      return `
        <div class="tech-detail ${isExpanded ? 'expanded' : ''}" data-index="${idx}">
          <div class="tech-header" onclick="ResultView.toggleDetail(${idx})">
            <div class="tech-info">
              <span class="tech-label">${item.label}</span>
              <div class="tech-value">${item.value}</div>
            </div>
            <div class="tech-actions">
              <span class="status-badge-sm ${item.status}">${item.status}</span>
              ${Icons.chevronDown('chevron')}
            </div>
          </div>
          ${isExpanded && item.explanation ? `
            <div class="tech-explanation">
              <div class="explanation-box ${item.status}">
                ${Icons.info()}
                <div>
                  <span class="explanation-title">Analysis Insight:</span>
                  ${item.explanation}
                </div>
              </div>
            </div>
          ` : ''}
        </div>`;
    }).join('');
  },

  // Toggle detail expansion
  toggleDetail(idx) {
    if (this.expandedDetails.has(idx)) {
      this.expandedDetails.delete(idx);
    } else {
      this.expandedDetails.add(idx);
    }
    document.getElementById('techDetails').innerHTML =
      this.renderTechDetails(this.currentResult.technicalDetails);
  },

  // Show feedback form
  showFeedbackForm() {
    const section = document.getElementById('feedbackSection');

    // Common patterns by media type
    const patterns = {
      image: [
        'Hands have wrong number of fingers',
        'Unnatural face/eyes',
        'Inconsistent lighting/shadows',
        'Blurry or distorted background',
        'Text is garbled/unreadable',
        'Clothing/accessories look wrong'
      ],
      video: [
        'Lip sync is off',
        'Face flickers or morphs',
        'Unnatural blinking',
        'Audio doesn\'t match video',
        'Edges around face are blurry',
        'Lighting changes unnaturally'
      ],
      audio: [
        'Unnatural pauses/rhythm',
        'Voice sounds robotic',
        'Background noise is inconsistent',
        'Breathing sounds wrong',
        'Emotional tone is flat'
      ],
      text: [
        'Contains false claims',
        'Logical inconsistencies',
        'Writing style is unnatural',
        'Factual errors',
        'Appears AI-generated'
      ]
    };

    const typePatterns = patterns[this.mediaType] || patterns.text;

    section.innerHTML = `
      <div class="feedback-form">
        <h4>${Icons.shieldCheck()} Teach Veritas System</h4>
        <p>Select the correct verdict:</p>
        <div class="verdict-buttons">
          <button class="verdict-btn ${this.localVerdict === 'Authentic' ? 'selected-real' : ''}" 
                  onclick="ResultView.setVerdict('Authentic')">Actually Real</button>
          <button class="verdict-btn ${this.localVerdict === 'AI-Generated' ? 'selected-fake' : ''}" 
                  onclick="ResultView.setVerdict('AI-Generated')">Actually Fake</button>
        </div>
        <label class="feedback-label">What did you notice? (optional)</label>
        <div class="pattern-chips" id="patternChips">
          ${typePatterns.map(p => `<button class="pattern-chip" onclick="ResultView.selectPattern('${p}')">${p}</button>`).join('')}
        </div>
        <input type="hidden" id="feedbackReason" value="">
        <div class="selected-pattern" id="selectedPattern" style="display:none;">
          Selected: <span id="selectedPatternText"></span>
        </div>
        <div class="feedback-actions">
          <button class="btn-cancel" onclick="ResultView.cancelFeedback()">Cancel</button>
          <button class="btn-submit" onclick="ResultView.submitFeedback()">Submit</button>
        </div>
      </div>`;
  },

  selectPattern(pattern) {
    document.getElementById('feedbackReason').value = pattern;
    document.querySelectorAll('.pattern-chip').forEach(c => c.classList.remove('selected'));
    event.target.classList.add('selected');
    document.getElementById('selectedPattern').style.display = 'block';
    document.getElementById('selectedPatternText').textContent = pattern;
  },

  setVerdict(verdict) {
    this.localVerdict = verdict;
    document.querySelectorAll('.verdict-btn').forEach(btn => {
      btn.classList.remove('selected-real', 'selected-fake');
    });
    event.target.classList.add(verdict === 'Authentic' ? 'selected-real' : 'selected-fake');
  },

  cancelFeedback() {
    document.getElementById('feedbackSection').innerHTML = `
      <button class="btn-report" onclick="ResultView.showFeedbackForm()">
        ${Icons.alertTriangle()}
        Report Incorrect Verdict
      </button>`;
  },

  async submitFeedback() {
    const reason = document.getElementById('feedbackReason').value.trim();

    // Use generic pattern if none selected
    const pattern = reason || `Verdict corrected to ${this.localVerdict}`;

    // Send to backend for persistent learning
    try {
      const response = await fetch('http://localhost:5000/api/learn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: this.mediaType || 'text',
          pattern: pattern,
          verdict: this.localVerdict,
          confidence: reason ? 90 : 70,  // Lower confidence if no specific pattern
          originalVerdict: this.currentResult?.verdict,
          example: this.currentResult?.summary?.substring(0, 200)
        })
      });

      if (response.ok) {
        document.getElementById('feedbackSection').innerHTML = `
          <div class="feedback-success">
            <h4>Thanks for the feedback!</h4>
            <p>${reason ? 'Pattern learned and saved.' : 'Verdict correction recorded.'}</p>
          </div>`;
      } else {
        throw new Error('Failed to save');
      }
    } catch (e) {
      // Fallback to local storage
      if (reason) {
        App.addLearningRule(`If "${reason}", verdict is likely ${this.localVerdict}.`);
      }
      document.getElementById('feedbackSection').innerHTML = `
        <div class="feedback-success">
          <h4>Feedback Saved</h4>
          <p>Your correction has been noted.</p>
        </div>`;
    }
  }
};
