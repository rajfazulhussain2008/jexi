// utils.js — Utility Functions

const utils = {
    formatDate(dateStr) {
        if (!dateStr) return "";
        const options = { year: 'numeric', month: 'long', day: 'numeric' };
        return new Date(dateStr).toLocaleDateString(undefined, options);
    },

    formatTime(dateStr) {
        if (!dateStr) return "";
        const options = { hour: 'numeric', minute: '2-digit' };
        return new Date(dateStr).toLocaleTimeString(undefined, options);
    },

    timeAgo(dateStr) {
        if (!dateStr) return "";
        const date = new Date(dateStr);
        const seconds = Math.floor((new Date() - date) / 1000);
        let interval = seconds / 31536000;
        if (interval > 1) return Math.floor(interval) + " years ago";
        interval = seconds / 2592000;
        if (interval > 1) return Math.floor(interval) + " months ago";
        interval = seconds / 86400;
        if (interval > 1) return Math.floor(interval) + " days ago";
        interval = seconds / 3600;
        if (interval > 1) return Math.floor(interval) + " hours ago";
        interval = seconds / 60;
        if (interval > 1) return Math.floor(interval) + " minutes ago";
        return Math.floor(seconds) + " seconds ago";
    },

    formatCurrency(amount) {
        // Simple logic: uses local storage pref or defaults to USD
        const pref = this.getFromLocal("jexi_currency") || "USD";
        if (pref === "INR") return "₹" + amount.toLocaleString('en-IN');
        return "$" + amount.toLocaleString('en-US');
    },

    debounce(func, delay) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    },

    generateId() {
        return "sess_" + Math.random().toString(36).substr(2, 9);
    },

    markdownToHtml(text) {
        if (!text) return "";
        let html = text;
        // Code blocks
        html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        // Bold
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        // Italic
        html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        // Numbered lists (basic)
        html = html.replace(/^\d+\.\s+(.*)$/gm, '<ol><li>$1</li></ol>');
        html = html.replace(/<\/ol>\n<ol>/g, ''); // combine consecutive ol
        // Bullet lists
        html = html.replace(/^-\s+(.*)$/gm, '<ul><li>$1</li></ul>');
        html = html.replace(/<\/ul>\n<ul>/g, ''); // combine consecutive ul
        // Newlines
        html = html.replace(/\n/g, '<br>');

        // Clean up redundant br tags inside pre/ul/ol
        html = html.replace(/<pre><code><br>/g, '<pre><code>');
        html = html.replace(/(<\/li><\/ul>)<br>/g, '$1');
        html = html.replace(/(<\/li><\/ol>)<br>/g, '$1');

        return html;
    },

    showToast(message, type = "info") {
        const toastContainer = document.getElementById("toast-container") || this.createToastContainer();

        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        toast.textContent = message;

        // Basic styles applied inline if not in CSS, assuming CSS handles `.toast` and `.toast-*`
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.classList.add("fade-out");
            setTimeout(() => {
                if (toast.parentElement) toast.remove();
            }, 300);
        }, 4000);
    },

    createToastContainer() {
        const container = document.createElement("div");
        container.id = "toast-container";
        container.style.position = "fixed";
        container.style.top = "20px";
        container.style.right = "20px";
        container.style.zIndex = "9999";
        container.style.display = "flex";
        container.style.flexDirection = "column";
        container.style.gap = "10px";
        document.body.appendChild(container);
        return container;
    },

    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = "flex";
            modal.classList.add("modal-enter");
        }
    },

    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = "none";
            modal.classList.remove("modal-enter");
        }
    },

    showLoading(containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = '<div class="spinner"></div>';
        }
    },

    hideLoading(containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            const spinner = container.querySelector('.spinner');
            if (spinner) spinner.remove();
        }
    },

    saveToLocal(key, value) {
        localStorage.setItem(key, JSON.stringify(value));
    },

    getFromLocal(key) {
        const item = localStorage.getItem(key);
        try {
            return item ? JSON.parse(item) : null;
        } catch (e) {
            return item; // in case it was saved as plain string
        }
    },

    removeFromLocal(key) {
        localStorage.removeItem(key);
    },

    updateSyncStatus(status) {
        const indicator = document.getElementById("globalSyncStatus");
        if (!indicator) return;
        const dot = indicator.querySelector(".sync-dot");
        const text = indicator.querySelector(".sync-text");

        dot.className = "sync-dot " + status;
        if (status === "online") {
            text.textContent = "Cloud Synchronized";
        } else if (status === "offline") {
            text.textContent = "Local Only (Offline)";
        } else if (status === "syncing") {
            text.textContent = "Synchronizing...";
        }
    },

    // --- Offline Storage (IndexedDB) ---
    openDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open("JEXI_DB", 1);
            request.onerror = () => reject("IndexedDB error");
            request.onupgradeneeded = (e) => {
                const db = e.target.result;
                if (!db.objectStoreNames.contains("cache")) db.createObjectStore("cache");
                if (!db.objectStoreNames.contains("chats")) db.createObjectStore("chats");
            };
            request.onsuccess = (e) => resolve(e.target.result);
        });
    },

    async saveToDB(storeName, key, data) {
        const db = await this.openDB();
        const tx = db.transaction(storeName, "readwrite");
        tx.objectStore(storeName).put(data, key);
        return new Promise((res) => tx.oncomplete = () => res(true));
    },

    async getFromDB(storeName, key) {
        const db = await this.openDB();
        return new Promise((res) => {
            const tx = db.transaction(storeName, "readonly");
            const req = tx.objectStore(storeName).get(key);
            req.onsuccess = () => res(req.result);
        });
    }
};

// Global escape key handler to close modals
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        const modals = document.querySelectorAll(".modal");
        modals.forEach(m => {
            if (m.style.display === "flex" || m.style.display === "block") {
                m.style.display = "none";
            }
        });
    }
});
