// settings.js — App Config, API Status & Auth Terminations

window.settingsHandler = {
    async loadSettings() {
        try {
            // A comprehensive app would GET /api/v1/auth/me but we use local vars for non-secure UI binds
            const theme = utils.getFromLocal("jexi_theme") || "dark";
            const voice = utils.getFromLocal("jexi_voice_enabled") === true;
            const curr = utils.getFromLocal("jexi_currency") || "USD";

            document.getElementById("settings-theme").value = theme;
            document.getElementById("settings-voice").checked = voice;
            document.getElementById("settings-currency").value = curr;

            this.loadProviderStatus();
        } catch (e) { }
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
});
