// settings.js — App Config, API Status & Auth Terminations

window.settingsHandler = {
    async loadSettings() {
        try {
            const theme = utils.getFromLocal("jexi_theme") || "dark";
            const voice = utils.getFromLocal("jexi_voice_enabled") === true;
            const curr = utils.getFromLocal("jexi_currency") || "USD";

            document.getElementById("settings-theme").value = theme;
            document.getElementById("settings-voice").checked = voice;
            document.getElementById("settings-currency").value = curr;

            this.loadProviderStatus();
            this.loadSessions();
        } catch (e) { }
    },

    async loadSessions() {
        const list = document.getElementById("activeSessionsList");
        if (!list) return;

        try {
            const response = await api.get("/auth/sessions");
            const sessions = response?.data || [];

            if (sessions.length === 0) {
                list.innerHTML = "<div class='text-center p-3 opacity-50'>No active sessions found.</div>";
                return;
            }

            // Get current token payload to identify "This Device"
            const token = localStorage.getItem("jexi_token");
            let currentJti = null;
            if (token) {
                try {
                    const payload = JSON.parse(atob(token.split('.')[1]));
                    currentJti = payload.jti;
                } catch (e) { }
            }

            list.innerHTML = sessions.map(s => {
                const isCurrent = s.token_jti === currentJti;
                const date = s.created_at ? new Date(s.created_at).toLocaleString() : "Unknown date";

                // Simple parser for UA to make it friendlier
                let device = "Unknown Device";
                if (s.user_agent) {
                    if (s.user_agent.includes("Mobi")) device = "Mobile Device";
                    else if (s.user_agent.includes("Windows")) device = "Windows PC";
                    else if (s.user_agent.includes("Macintosh")) device = "Mac";
                    else if (s.user_agent.includes("Linux")) device = "Linux PC";
                }

                return `
                    <div class="session-item">
                        <div class="session-info">
                            <div class="session-device">
                                <i class="fas ${s.user_agent?.includes("Mobi") ? 'fa-mobile-alt' : 'fa-laptop'}"></i> 
                                ${device}
                                ${isCurrent ? '<span class="current-session-badge">This Device</span>' : ''}
                            </div>
                            <div class="session-meta">
                                <span>IP: ${s.ip_address || "Unknown"}</span> • 
                                <span>Login: ${date}</span>
                            </div>
                        </div>
                        ${!isCurrent ? `
                            <button class="btn-icon text-red" onclick="window.settingsHandler.revokeSession(${s.id})" title="Revoke Session">
                                <i class="fas fa-sign-out-alt"></i>
                            </button>
                        ` : ''}
                    </div>
                `;
            }).join("");

        } catch (e) {
            list.innerHTML = "<div class='text-center p-3 text-danger'>Failed to load sessions.</div>";
        }
    },

    async revokeSession(id) {
        if (!confirm("Are you sure you want to log out this device remotely?")) return;

        try {
            utils.showToast("Revoking session...", "info");
            await api.post(`/auth/sessions/${id}/revoke`);
            utils.showToast("Session revoked.", "success");
            this.loadSessions();
        } catch (e) {
            utils.showToast("Failed to revoke session.", "error");
        }
    },

    async logoutAllDevices() {
        if (!confirm("This will log you out of EVERY device except this one. Continue?")) return;

        try {
            utils.showToast("Clearing other sessions...", "info");
            await api.post("/auth/logout-all");
            utils.showToast("All other sessions revoked.", "success");
            this.loadSessions();
        } catch (e) {
            utils.showToast("Failed to clear sessions.", "error");
        }
    },

    saveSettings() {
        const t = document.getElementById("settings-theme").value;
        const v = document.getElementById("settings-voice").checked;
        const c = document.getElementById("settings-currency").value;

        app.setTheme(t);
        utils.saveToLocal("jexi_voice_enabled", v);
        utils.saveToLocal("jexi_currency", c);

        utils.showToast("Settings preserved permanently.", "success");

        // Also update chat toggle if it exists globally
        if (window.chatHandler) window.chatHandler.voiceEnabled = v;
    },

    async loadProviderStatus() {
        const c = document.getElementById("settings-provider-status");
        if (!c) return;

        try {
            c.innerHTML = "Fetching model connection lines...";
            // Explicit endpoint checking the dynamic LLMRouter priority loadouts
            const p = await api.get("/ai/providers/stats");

            let html = `<div class="grid col-2 gap-2 mt-2">`;
            for (const [provider, stats] of Object.entries(p)) {
                // If weight block is > 0 and initialized success config found
                const active = stats.keys_total > 0;
                html += `
                    <div class="card p-2 text-sm flex gap-2 align-center">
                        <span style="color: ${active ? 'var(--success)' : 'var(--danger)'}">●</span>
                        <strong class="uppercase">${provider}</strong>
                        <span class="opacity-50 float-right">Wt: ${stats.weight.toFixed(1)}</span>
                    </div>
                `;
            }
            html += `</div>`;
            c.innerHTML = html;
        } catch (e) {
            c.innerHTML = "<small class='text-danger'>Provider registry inaccessible.</small>";
        }
    },

    handleLogout() {
        api.logout();
    },

    async resetData() {
        const code = prompt("Factory Wipe will destroy all metrics, code logs, and history.\nType 'DELETE' to confirm:");
        if (code !== "DELETE") {
            utils.showToast("Abort successful", "info");
            return;
        }

        // Explicitly hit the hardest endpoint.
        utils.showToast("Initiating purge sequence...", "warning");
        try {
            await api.del("/settings/reset");
            utils.showToast("Database zeroed. Initiating logoff...", "info");
            setTimeout(() => {
                api.logout();
            }, 1000);
        } catch (e) { }
    },

    async addFriendKey() {
        const provider = document.getElementById("friendKeyProvider").value;
        const key = document.getElementById("friendKeyInput").value;

        if (!key) {
            utils.showToast("Please enter an API key", "warning");
            return;
        }

        try {
            utils.showToast("Encrypting and adding key to pool...", "info");
            const response = await api.post("/social/keys", { provider, key });

            if (response && response.message) {
                utils.showToast("Successfully added your key to the rotation pool! 🚀", "success");
                document.getElementById("friendKeyInput").value = "";
                // Refresh pool status if we had a list, for now justToast
                this.loadProviderStatus();
            }
        } catch (e) {
            console.error("Failed to add key:", e);
        }
    }
};

// Initialize listeners for settings
document.addEventListener("DOMContentLoaded", () => {
    const submitBtn = document.getElementById("submitFriendKeyBtn");
    if (submitBtn) {
        submitBtn.addEventListener("click", () => window.settingsHandler.addFriendKey());
    }

    const logoutAllBtn = document.getElementById("logoutAllBtn");
    if (logoutAllBtn) {
        logoutAllBtn.addEventListener("click", () => window.settingsHandler.logoutAllDevices());
    }
});
