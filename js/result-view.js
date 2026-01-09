/**
 * VERITAS - Result View Module
 * Handles rendering of verification results
 */

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
    const isSuspicious = result.verdict === 'Fake/Generated' || result.verdict === 'Suspicious';
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
          <button class="verdict-btn ${this.localVerdict === 'Fake/Generated' ? 'selected-fake' : ''}" 
                  onclick="ResultView.setVerdict('Fake/Generated')">Actually Fake</button>
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
