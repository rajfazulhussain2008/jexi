// dev.js — Multi-Modal IDE Emulation & Pair Programming

window.devHandler = {
    currentMode: "pair",
    currentProjectId: null,
    activeSessionId: null,
    sessionTimer: null,
    sessionSeconds: 0,

    initDev() {
        // Load persistent state
        const storedSecs = utils.getFromLocal("jexi_dev_timer");
        const storedIsActive = utils.getFromLocal("jexi_dev_timer_active");

        if (storedSecs) {
            this.sessionSeconds = parseInt(storedSecs, 10);
            this.updateTimerDisplay();
        }

        if (storedIsActive) {
            this.startSession(true); // resume silently
        }

        // Setup Mode Toggles
        const modes = document.querySelectorAll(".dev-mode-btn");
        modes.forEach(btn => {
            btn.onclick = () => {
                modes.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                this.selectMode(btn.dataset.mode);
            };
        });

        this.loadDevStats();
        this.loadHeatmap();
    },

    switchDevTab(tab) {
        document.querySelectorAll(".dev-tab-pane").forEach(p => p.style.display = "none");
        document.querySelectorAll(".dev-nav-tab").forEach(t => t.classList.remove("active"));

        const target = document.getElementById(`dev-tab-${tab}`);
        const btn = document.querySelector(`.dev-nav-tab[data-target="${tab}"]`);

        if (target) target.style.display = "block";
        if (btn) btn.classList.add("active");

        // Lazy load intensive tabs
        if (tab === "stats") {
            this.loadProductivityByHour();
            this.loadSkillTree();
        }
    },

    selectMode(mode) {
        this.currentMode = mode;
        const root = document.documentElement;

        // Dynamic Accent Colors based on AI persona
        const colors = {
            "pair": "#10B981",    // Green: Collaborative
            "teacher": "#3B82F6", // Blue: Educational
            "reviewer": "#F59E0B",// Orange: Strict
            "debug": "#EF4444",   // Red: Error diagnosing
            "speed": "#8B5CF6",   // Purple: Max output
            "challenge": "#6366F1"// Indigo: Leetcode
        };

        if (colors[mode]) {
            root.style.setProperty('--accent', colors[mode]);
        }

        utils.showToast(`${mode.charAt(0).toUpperCase() + mode.slice(1)} Mode Activated`, "info");
    },

    // Session Timer
    startSession(resume = false) {
        if (!resume) {
            this.sessionSeconds = 0;
            // Ideally: POST /api/v1/dev/sessions/start
        }

        clearInterval(this.sessionTimer);
        this.sessionTimer = setInterval(() => {
            this.sessionSeconds++;
            this.updateTimerDisplay();
            utils.saveToLocal("jexi_dev_timer", this.sessionSeconds);
            utils.saveToLocal("jexi_dev_timer_active", true);
        }, 1000);

        document.getElementById("dev-timer-btn").textContent = "Pause Session";
        document.getElementById("dev-timer-btn").onclick = () => this.pauseSession();
    },

    pauseSession() {
        clearInterval(this.sessionTimer);
        utils.saveToLocal("jexi_dev_timer_active", false);
        document.getElementById("dev-timer-btn").textContent = "Resume Session";
        document.getElementById("dev-timer-btn").onclick = () => this.startSession(true);
    },

    endSession() {
        clearInterval(this.sessionTimer);
        utils.removeFromLocal("jexi_dev_timer");
        utils.removeFromLocal("jexi_dev_timer_active");

        const time = this.formatTimer(this.sessionSeconds);
        utils.showToast(`Session ended. Time: ${time}`, "success");

        this.sessionSeconds = 0;
        this.updateTimerDisplay();
        document.getElementById("dev-timer-btn").textContent = "Start Session";
        document.getElementById("dev-timer-btn").onclick = () => this.startSession();

        // POST /api/v1/dev/sessions/end
    },

    updateTimerDisplay() {
        const d = document.getElementById("dev-timer-display");
        if (d) d.textContent = this.formatTimer(this.sessionSeconds);
    },

    formatTimer(sec) {
        let h = Math.floor(sec / 3600);
        let m = Math.floor((sec % 3600) / 60);
        let s = sec % 60;
        return [h, m, s].map(v => v < 10 ? "0" + v : v).join(":");
    },

    // Dev Chat
    async sendDevMessage() {
        const input = document.getElementById("dev-chat-input");
        const msg = input.value.trim();
        if (!msg) return;

        // Add to UI immediately
        this.addDevChatBubble("user", msg);
        input.value = "";

        const codeContext = document.getElementById("dev-code-context")?.value || "";
        const errorMsg = document.getElementById("dev-error-context")?.value || "";

        try {
            utils.showToast("Compiling Context...", "info");
            const res = await api.post("/dev/chat", {
                message: msg,
                mode: this.currentMode,
                project_id: this.currentProjectId,
                code_context: codeContext,
                error_message: errorMsg,
                session_id: "dev_" + utils.generateId()
            });

            this.addDevChatBubble("assistant", res.text);
        } catch (e) { }
    },

    addDevChatBubble(role, htmlStr) {
        const c = document.getElementById("dev-chat-messages");
        if (!c) return;

        const div = document.createElement("div");
        div.className = `chat-bubble chat-bubble-${role} fade-in`;

        // Special formatting for code blocks in Dev mode
        let parsedHtml = utils.markdownToHtml(htmlStr);
        // Extremely rudimentary syntax highlight simulation
        parsedHtml = parsedHtml.replace(/def (.*?)\(/g, "<span style='color:#3B82F6'>def</span> <span style='color:#F59E0B'>$1</span>(");
        parsedHtml = parsedHtml.replace(/import (.*?)</g, "<span style='color:#8B5CF6'>import</span> $1<");

        div.innerHTML = `<div class="chat-content">${parsedHtml}</div>`;
        c.appendChild(div);
        c.scrollTop = c.scrollHeight;
    },

    // Review Submodule
    async submitReview() {
        const code = document.getElementById("dev-review-code").value;
        const lang = document.getElementById("dev-review-lang").value;
        const focus = document.getElementById("dev-review-focus").value;

        if (!code) return;

        utils.showLoading("dev-review-results");
        try {
            const res = await api.post("/dev/review", { code, language: lang, focus });
            utils.hideLoading("dev-review-results");
            this.renderReviewResults(res);
        } catch (e) { }
    },

    renderReviewResults(r) {
        const c = document.getElementById("dev-review-results");
        if (!c) return;

        let html = `<h4>Review Complete</h4>`;

        if (r.scores) {
            html += `<div class="grid col-3 gap-2 mt-2 mb-3">`;
            for (const [k, v] of Object.entries(r.scores)) {
                html += `<div class="card bg-surface-dark text-center">
                    <small>${k.toUpperCase()}</small>
                    <h3 class="${v > 7 ? 'text-success' : 'text-warning'}">${v}/10</h3>
                </div>`;
            }
            html += `</div>`;
        }

        if (r.issues && r.issues.length) {
            html += `<div class="alert alert-warning mb-2"><strong>Issues:</strong><ul>`;
            r.issues.forEach(i => html += `<li>${i}</li>`);
            html += `</ul></div>`;
        }

        if (r.suggestions && r.suggestions.length) {
            html += `<div class="alert alert-info"><strong>Suggestions:</strong><ul>`;
            r.suggestions.forEach(s => html += `<li>${s}</li>`);
            html += `</ul></div>`;
        }

        c.innerHTML = html;
    },

    // Debugging
    async submitDebug() {
        const code = document.getElementById("dev-debug-code").value;
        const err = document.getElementById("dev-debug-error").value;

        if (!code || !err) return utils.showToast("Both code and error trace needed", "warning");

        utils.showLoading("dev-debug-results");
        try {
            const res = await api.post("/dev/debug", { code, language: "python", error: err });
            utils.hideLoading("dev-debug-results");

            const c = document.getElementById("dev-debug-results");
            c.innerHTML = `
                <div class="alert alert-danger mb-2"><strong>Root Cause:</strong><br>${res.root_cause || 'Unknown'}</div>
                <div class="alert alert-success mb-2"><strong>Fix:</strong><br><pre><code>${res.fix_code || ''}</code></pre></div>
                <div class="alert alert-info"><strong>Prevention:</strong><br>${res.prevention || ''}</div>
            `;
        } catch (e) { }
    },

    // DSA
    async loadChallenge() {
        const diff = document.getElementById("dev-dsa-diff").value;
        const topic = document.getElementById("dev-dsa-topic").value;

        utils.showLoading("dev-dsa-problem");
        try {
            const prob = await api.get(`/dev/challenge?difficulty=${diff}&topic=${topic}`);
            utils.hideLoading("dev-dsa-problem");

            document.getElementById("dev-dsa-id").value = prob.id || 0;
            const c = document.getElementById("dev-dsa-problem");

            c.innerHTML = `
                <h4>${prob.title} <span class="badge ${diff === 'Hard' ? 'badge-danger' : 'badge-primary'}">${diff}</span></h4>
                <p>${prob.description}</p>
                <h5>Examples:</h5>
                <ul>${(prob.examples || []).map(ex => `<li><code>${ex}</code></li>`).join('')}</ul>
            `;

            window._currentHints = prob.hints || [];
            document.getElementById("dev-dsa-hints").innerHTML =
                `<button class="btn btn-sm btn-outline mt-2" onclick="window.devHandler.showHint()">Get Hint</button> <span id="hint-text" class="text-sm"></span>`;

        } catch (e) { }
    },

    showHint() {
        if (!window._currentHints || !window._currentHints.length) {
            document.getElementById("hint-text").textContent = "No more hints!";
            return;
        }
        document.getElementById("hint-text").textContent = " " + window._currentHints.shift();
    },

    async submitSolution() {
        const code = document.getElementById("dev-dsa-solution").value;
        const pid = document.getElementById("dev-dsa-id").value;

        if (!pid) return utils.showToast("Load a problem first", "warning");

        utils.showLoading("dev-dsa-eval");
        try {
            const ev = await api.post("/dev/challenge/submit", { problem_id: parseInt(pid), code });
            utils.hideLoading("dev-dsa-eval");

            const c = document.getElementById("dev-dsa-eval");
            c.innerHTML = `
                <div class="alert ${ev.correctness ? 'alert-success' : 'alert-danger'}">
                    <h4>${ev.correctness ? '✅ Tests Passed' : '❌ Tests Failed'}</h4>
                    <p><strong>Time:</strong> ${ev.time_complexity || 'O(?)'} | <strong>Space:</strong> ${ev.space_complexity || 'O(?)'}</p>
                    <p>${ev.feedback}</p>
                    <p><small class="opacity-75">vs Optimal: ${ev.compare_to_optimal}</small></p>
                </div>
            `;
        } catch (e) { }
    },

    // Stats
    async loadDevStats() {
        try {
            const s = await api.get("/dev/stats");
            const c = document.getElementById("dev-stats-overview");
            if (c && s) {
                c.innerHTML = `
                    Total Hours: <strong>${Math.round(s.total_coding_hours || 0)}h</strong> | 
                    Sessions: <strong>${s.sessions_count || 0}</strong>
                `;
            }
        } catch (e) { }
    },

    async loadHeatmap() {
        const container = document.getElementById("dev-heatmap");
        if (!container) return;

        try {
            // Simplified Github style heatmap grid (365 squares)
            const map = await api.get("/dev/stats/heatmap?year=2025");
            // If API not implemented, mock logic for UI satisfaction
            container.innerHTML = "";
            container.style.display = "grid";
            container.style.gridTemplateColumns = "repeat(52, 1fr)";
            container.style.gap = "3px";

            for (let i = 0; i < 364; i++) {
                const day = document.createElement("div");
                day.style.width = "10px";
                day.style.height = "10px";
                day.style.borderRadius = "2px";
                day.style.backgroundColor = Math.random() > 0.8 ? "var(--primary)" :
                    Math.random() > 0.9 ? "var(--accent)" : "rgba(255,255,255,0.05)";
                container.appendChild(day);
            }
        } catch (e) { }
    },

    async loadProductivityByHour() {
        // Chart mapping hours 0-23
    },

    async loadSkillTree() {
        // Hierarchical rendering
    }
};
