/**
 * VERITAS - API Service
 * Connects to Python Flask backend for Groq AI analysis
 */

const GroqService = {
    API_KEY: '',
    BACKEND_URL: 'http://localhost:5000',
    USE_BACKEND: true,  // Set to true to use Python backend

    // Direct Groq API (fallback if backend not available)
    GROQ_API_URL: 'https://api.groq.com/openai/v1/chat/completions',
    MODELS: {
        text: 'llama-3.3-70b-versatile',
        image: 'llama-3.3-70b-versatile',
        video: 'llama-3.3-70b-versatile',
        audio: 'whisper-large-v3-turbo'
    },

    setApiKey(key) {
        this.API_KEY = key;
        localStorage.setItem('veritas_api_key', key);
    },

    getApiKey() {
        if (!this.API_KEY) {
            this.API_KEY = localStorage.getItem('veritas_api_key') || '';
        }
        return this.API_KEY;
    },

    hasApiKey() {
        // If using backend, we don't need API key in frontend
        if (this.USE_BACKEND) return true;
        return !!this.getApiKey();
    },

    // Check if backend is available
    async checkBackend() {
        try {
            const response = await fetch(`${this.BACKEND_URL}/api/health`);
            return response.ok;
        } catch {
            return false;
        }
    },

    // Main verification function
    async verifyMedia(type, content, useSearch = false, userGuidelines = []) {
        // Try backend first
        if (this.USE_BACKEND) {
            const backendAvailable = await this.checkBackend();
            if (backendAvailable) {
                return this.verifyViaBackend(type, content, useSearch, userGuidelines);
            }
            console.log('Backend not available, falling back to direct API');
        }

        // Fallback to direct API
        return this.verifyViaDirect(type, content, useSearch, userGuidelines);
    },

    // Verify via Python backend
    async verifyViaBackend(type, content, useSearch, userGuidelines) {
        // Map tab types to backend endpoints
        let endpoint;
        if (type === 'ai-detect') {
            endpoint = `${this.BACKEND_URL}/api/detect/ai-text`;
        } else if (type === 'fact-check') {
            endpoint = `${this.BACKEND_URL}/api/verify/text`;
        } else {
            endpoint = `${this.BACKEND_URL}/api/verify/${type}`;
        }

        const isTextType = type === 'ai-detect' || type === 'fact-check';

        if (isTextType) {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: content,
                    useSearch: type === 'fact-check' ? useSearch : false,
                    userGuidelines
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Analysis failed');
            }

            return response.json();
        } else {
            // For files (image, video, audio)
            const formData = new FormData();
            formData.append('file', content);
            formData.append('useSearch', useSearch);

            const response = await fetch(endpoint, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Analysis failed');
            }

            return response.json();
        }
    },

    // Verify via direct Groq API (fallback)
    async verifyViaDirect(type, content, useSearch, userGuidelines) {
        const apiKey = this.getApiKey();
        if (!apiKey) {
            throw new Error('API key not configured');
        }

        const systemPrompt = this.buildSystemPrompt(type, useSearch, userGuidelines);
        const userMessage = this.buildUserMessage(type, content);

        const requestBody = {
            model: this.MODELS[type] || this.MODELS.text,
            messages: [
                { role: 'system', content: systemPrompt },
                { role: 'user', content: userMessage }
            ],
            temperature: 1,
            max_tokens: 1024
        };

        const response = await fetch(this.GROQ_API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error?.message || 'API request failed');
        }

        const data = await response.json();
        let responseText = data.choices?.[0]?.message?.content || '{}';

        const firstBrace = responseText.indexOf('{');
        const lastBrace = responseText.lastIndexOf('}');
        if (firstBrace !== -1 && lastBrace !== -1) {
            responseText = responseText.substring(firstBrace, lastBrace + 1);
        }

        return JSON.parse(responseText);
    },

    buildSystemPrompt(type, useSearch, userGuidelines) {
        let prompt = `You are Veritas, a media forensics AI. Analyze ${type} for authenticity.`;

        if (userGuidelines?.length > 0) {
            prompt += `\n\nUser rules:\n${userGuidelines.join('\n')}`;
        }

        prompt += `\n\nRespond with JSON only:
{
    "verdict": "Authentic"|"Fake/Generated"|"Inconclusive"|"Suspicious",
    "confidence": 0-100,
    "summary": "...",
    "reasoning": ["..."],
    "technicalDetails": [{"label":"...","value":"...","status":"pass|fail|warn","explanation":"..."}]
}`;
        return prompt;
    },

    buildUserMessage(type, content) {
        if (type === 'text') return `Analyze: ${content}`;
        return `Analyze ${type} file: ${content.name}, Size: ${(content.size / 1024).toFixed(1)}KB`;
    }
};

// Backward compatibility
const GeminiService = GroqService;
