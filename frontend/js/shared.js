/**
 * VERITAS - Shared Utilities
 * Common functions used across all pages
 */

const Veritas = {
    BACKEND_URL: 'http://localhost:5000',
    STORAGE_KEYS: {
        PENDING: 'veritas_pending_analysis',
        RESULT: 'veritas_result',
        HISTORY: 'veritas_history'
    },

    // ========== INPUT/OUTPUT STORAGE ==========

    /**
     * Save analysis input before redirecting to scanning page
     */
    saveInput(type, content, useSearch = false) {
        const data = {
            type,
            useSearch,
            timestamp: Date.now()
        };

        if (type === 'text') {
            data.text = content;
        } else {
            // For files, we need to convert to base64
            return new Promise((resolve) => {
                const reader = new FileReader();
                reader.onload = (e) => {
                    data.fileData = e.target.result;
                    data.fileName = content.name;
                    data.fileType = content.type;
                    localStorage.setItem(this.STORAGE_KEYS.PENDING, JSON.stringify(data));
                    resolve();
                };
                reader.readAsDataURL(content);
            });
        }

        localStorage.setItem(this.STORAGE_KEYS.PENDING, JSON.stringify(data));
        return Promise.resolve();
    },

    /**
     * Get pending analysis input
     */
    getInput() {
        const data = localStorage.getItem(this.STORAGE_KEYS.PENDING);
        return data ? JSON.parse(data) : null;
    },

    /**
     * Save analysis result
     */
    saveResult(result, thumbnail = null) {
        const data = {
            result,
            thumbnail,
            timestamp: Date.now()
        };
        localStorage.setItem(this.STORAGE_KEYS.RESULT, JSON.stringify(data));
    },

    /**
     * Get analysis result
     */
    getResult() {
        const data = localStorage.getItem(this.STORAGE_KEYS.RESULT);
        return data ? JSON.parse(data) : null;
    },

    /**
     * Clear pending analysis data
     */
    clearPending() {
        localStorage.removeItem(this.STORAGE_KEYS.PENDING);
    },

    // ========== HISTORY (Supabase API) ==========

    async getHistory() {
        try {
            const response = await fetch(`${this.BACKEND_URL}/api/history`);
            if (!response.ok) return [];
            const data = await response.json();
            return data.history || [];
        } catch (e) {
            console.error('Failed to fetch history:', e);
            return [];
        }
    },

    async deleteHistoryItem(id) {
        try {
            const response = await fetch(`${this.BACKEND_URL}/api/history/${id}`, {
                method: 'DELETE'
            });
            return response.ok;
        } catch (e) {
            console.error('Failed to delete history item:', e);
            return false;
        }
    },

    // Note: addToHistory is now handled by the backend during verification
    // This is kept for local fallback only
    addToHistory(item) {
        // No-op: history is now saved server-side
        console.log('History saved server-side');
    },

    clearHistory() {
        // No-op: clearing requires deleting each item via API
        console.warn('Use deleteHistoryItem to remove individual items');
    },

    // ========== API CALLS ==========

    /**
     * Call backend API for verification
     */
    async verify(type, content, useSearch = false) {
        const endpoint = `${this.BACKEND_URL}/api/verify/${type}`;

        if (type === 'text') {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: content, useSearch })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Analysis failed');
            }
            return response.json();
        } else {
            // For files
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

    /**
     * Check if backend is available
     */
    async checkBackend() {
        try {
            const response = await fetch(`${this.BACKEND_URL}/api/health`);
            return response.ok;
        } catch {
            return false;
        }
    },

    // ========== UTILITIES ==========

    /**
     * Convert base64 data URL back to File object
     */
    dataURLtoFile(dataUrl, filename) {
        const arr = dataUrl.split(',');
        const mime = arr[0].match(/:(.*?);/)[1];
        const bstr = atob(arr[1]);
        let n = bstr.length;
        const u8arr = new Uint8Array(n);
        while (n--) {
            u8arr[n] = bstr.charCodeAt(n);
        }
        return new File([u8arr], filename, { type: mime });
    },

    /**
     * Generate thumbnail from file
     */
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
