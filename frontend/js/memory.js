// memory.js — Fact Extraction Tables & Passive AI Core Identity Builder

window.memoryHandler = {
    async loadMemory() {
        try {
            utils.showLoading("memory-facts-list");
            const facts = await api.get("/memory/facts");
            const c = document.getElementById("memory-facts-list");
            if (!c) return;

            c.innerHTML = "";
            if (!facts || facts.length === 0) {
                c.innerHTML = "<p class='empty-state text-sm'>No passive facts extracted. Start chatting in Dev or Main AI to seed the memory graph.</p>";
                return;
            }

            facts.forEach(f => {
                c.innerHTML += `
                    <div class="card mb-2 flex-between p-2">
                        <div>
                            <span class="badge badge-accent text-xs mb-1">${f.key}</span>
                            <div class="text-sm font-mono mt-1">${f.value}</div>
                            <div class="text-xs opacity-25 mt-1">${f.source || 'sys'} • ${utils.formatDate(f.updated_at)}</div>
                        </div>
                        <button class="btn btn-ghost btn-sm text-danger" onclick="window.memoryHandler.deleteFact('${f.key}')">×</button>
                    </div>
                `;
            });
            utils.hideLoading("memory-facts-list");
        } catch (e) {
            utils.hideLoading("memory-facts-list");
        }
    },

    async saveFact() {
        const key = prompt("Enter Memory Key (e.g., 'diet_preference'):");
        if (!key) return;
        const val = prompt("Enter the Value:");
        if (!val) return;

        try {
            await api.post("/memory/facts", {
                facts: { [key]: val },
                source: "manual"
            });
            this.loadMemory();
            utils.showToast(`Injected key: ${key}`, "success");
        } catch (e) { }
    },

    async deleteFact(key) {
        if (!confirm(`Wipe "${key}" from AI Memory core?`)) return;
        try {
            await api.del(`/memory/facts/${key}`);
            this.loadMemory();
        } catch (e) { }
    }
};
