// planner.js — External API Briefings & Time-Boxed Segments

window.plannerHandler = {
    async loadPlanner() {
        this.loadMorningBriefing();
        this.generateSchedule(); // Default generation locally
    },

    async loadMorningBriefing() {
        try {
            utils.showLoading("planner-briefing");
            const brief = await api.get("/planner/morning-briefing");

            const c = document.getElementById("planner-briefing");
            if (!c) return;

            let wData = brief.weather ?
                `<strong>Weather:</strong> ${brief.weather.temp}°C, ${brief.weather.description}` : "";

            c.innerHTML = `
                <div class="card bg-surface-dark bg-gradient mb-3 p-4 border-accent">
                    <h3 class="m-0 text-accent">Morning Briefing</h3>
                    <p class="text-sm opacity-75 mt-1">${wData}</p>
                    <hr class="opacity-25 my-3">
                    <p class="text-lg italic text-center">"${utils.markdownToHtml(brief.motivational_message)}"</p>
                    <div class="text-right mt-2 text-xs opacity-50">Yesterday's Score: ${Math.round(brief.yesterday_score || 0)}</div>
                </div>
            `;
            utils.hideLoading("planner-briefing");
        } catch (e) {
            utils.hideLoading("planner-briefing");
        }
    },

    async generateSchedule() {
        const c = document.getElementById("planner-schedule-list");
        if (!c) return;

        try {
            utils.showLoading("planner-schedule-list");
            // Standard available hours request dynamically fetched from user preferences,
            // Hard coded to 4 block hours for immediate generative prototyping without prompting.
            const sched = await api.post("/planner/generate-schedule", { available_hours: 4 });

            c.innerHTML = "";
            if (!sched || sched.length === 0) {
                c.innerHTML = "<p>No tasks mapped for scheduling. You have free time!</p>";
                return;
            }

            const isBreak = t => t.type === "break" || t.activity.toLowerCase().includes("break");

            sched.forEach(block => {
                c.innerHTML += `
                    <div class="flex-between mb-3 border-left p-2 round ${isBreak(block) ? 'border-success opacity-75' : 'bg-surface'}">
                        <div>
                            <strong class="text-accent mr-3">${block.time}</strong>
                            <span>${block.activity}</span>
                        </div>
                        <div class="text-xs opacity-50">${block.duration}m</div>
                    </div>
                `;
            });
            utils.hideLoading("planner-schedule-list");
        } catch (e) {
            utils.hideLoading("planner-schedule-list");
            c.innerHTML = "<small class='text-danger'>Schedule mapping failed due to strict JSON parsing timeouts.</small>";
        }
    },

    async startFocusSession() {
        const id = prompt("Enter Task ID to focus on (Optional):");
        const t = prompt("Minutes?", "25");
        if (!t) return;

        utils.showToast(`Started Focus timer for ${t} minutes.`, "success");
        // We'd fire a setInterval here updating DOM text,
        // and issue api.post('/planner/focus-mode/end') asynchronously upon finishing.
    }
};
