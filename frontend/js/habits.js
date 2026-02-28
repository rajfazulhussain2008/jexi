// habits.js — Continuous Streak Tracker

window.habitsHandler = {
    async loadHabits() {
        try {
            utils.showLoading("habits-list");
            const habits = await api.get("/habits/today");
            this.renderHabits(habits);
            utils.hideLoading("habits-list");

            // Load side panels implicitly
            this.loadStreaks();
        } catch (e) {
            utils.hideLoading("habits-list");
            const container = document.getElementById("habits-list");
            if (container) container.innerHTML = "<p>Failed to load habits.</p>";
        }
    },

    renderHabits(habitsData) {
        const container = document.getElementById("habits-list");
        if (!container) return;
        container.innerHTML = "";

        if (!habitsData || habitsData.length === 0) {
            container.innerHTML = "<p class='empty-state'>No habit trackers active.</p>";
            return;
        }

        habitsData.forEach(data => {
            const h = data.habit;
            const done = data.completed_today;

            const row = document.createElement("div");
            row.className = "flex-between card hover-scale mb-3";
            row.style.padding = "1rem";

            row.innerHTML = `
                <div class="flex align-center gap-3">
                    <div class="habit-icon" style="font-size: 1.5rem;">${h.icon || '📌'}</div>
                    <div>
                        <h4 class="m-0">${h.name}</h4>
                        <small class="text-xs opacity-75">${h.frequency}</small>
                    </div>
                </div>
                <div class="flex align-center gap-3">
                    <button class="btn btn-icon btn-circular ${done ? 'btn-success' : 'btn-outline'}" 
                            onclick="window.habitsHandler.toggleHabit(${h.id}, ${done})">
                        ${done ? '✓' : ''}
                    </button>
                </div>
            `;
            container.appendChild(row);
        });
    },

    async toggleHabit(id, isCurrentlyDone) {
        try {
            if (isCurrentlyDone) {
                await api.del(`/habits/${id}/check`);
                this.loadHabits();
            } else {
                const res = await api.post(`/habits/${id}/check`, {});
                this.loadHabits();

                // Fire confetto or milestone popup
                if (res && res.milestone_reached) {
                    utils.showToast(`🎉 Achievement Unlocked: ${res.milestone_type} streak!`, "success");
                } else if (res && res.streak > 1) {
                    utils.showToast(`🔥 Streak: ${res.streak} days. Keep it up!`, "info");
                }
            }
        } catch (e) { }
    },

    async loadStreaks() {
        const board = document.getElementById("habits-leaderboard");
        if (!board) return;

        try {
            const streaks = await api.get("/habits/streaks");
            if (!streaks.length) {
                board.innerHTML = "<small>No current streak data</small>";
                return;
            }

            board.innerHTML = "<h4>🔥 Active Streaks</h4><ul class='list-none p-0'>";
            streaks.sort((a, b) => b.streak - a.streak).forEach(s => {
                board.innerHTML += `<li class="flex-between mb-2"><span>${s.habit}</span> <span class="badge badge-accent">${s.streak} days</span></li>`;
            });
            board.innerHTML += "</ul>";
        } catch (e) {
            board.innerHTML = "<small>Could not load streaks</small>";
        }
    },

    async loadAIInsights() {
        try {
            utils.showToast("Analyzing habits...", "info");
            const text = await api.get("/habits/ai-insights");
            const panel = document.getElementById("habits-ai-panel");
            if (panel) panel.innerHTML = `<div class="alert alert-info border-left">${utils.markdownToHtml(text)}</div>`;
        } catch (e) { }
    },

    showAddHabitModal() {
        utils.showModal("habit-modal");
    },
    hideModal() {
        utils.hideModal("habit-modal");
    },

    async createHabit() {
        const name = document.getElementById("habit-name")?.value;
        const icon = document.getElementById("habit-icon")?.value || "✅";
        const freq = document.getElementById("habit-freq")?.value || "daily";

        if (!name) return utils.showToast("Name required", "error");

        try {
            await api.post("/habits", { name, icon, frequency: freq });
            this.hideModal();
            this.loadHabits();
        } catch (e) { }
    }
};
