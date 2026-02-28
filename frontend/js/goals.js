// goals.js — SMART Goal Hierarchy & Pacing

window.goalsHandler = {
    async loadGoals() {
        try {
            utils.showLoading("goals-list");
            const filter = document.getElementById("goals-filter")?.value || "";
            const query = filter ? `?status=${filter}` : "";

            const goals = await api.get(`/goals${query}`);
            this.renderGoals(goals);
            utils.hideLoading("goals-list");
        } catch (e) {
            utils.hideLoading("goals-list");
            document.getElementById("goals-list").innerHTML = "<p>Failed to load goals.</p>";
        }
    },

    renderGoals(goals) {
        const container = document.getElementById("goals-list");
        if (!container) return;
        container.innerHTML = "";

        if (!goals || goals.length === 0) {
            container.innerHTML = "<p class='empty-state'>No goals yet. Set your first vision!</p>";
            return;
        }

        goals.forEach(goal => {
            const card = document.createElement("div");
            card.className = "card goal-card fade-in";

            const percentage = goal.target_value ? Math.round((goal.current_value / goal.target_value) * 100) : 0;
            const barColor = percentage >= 100 ? "bg-success" : (percentage > 50 ? "bg-accent" : "bg-warning");

            card.innerHTML = `
                <div class="flex-between">
                    <h4>${utils.markdownToHtml(goal.title)}</h4>
                    <span class="badge ${goal.status === 'completed' ? 'badge-success' : 'badge-primary'}">${goal.goal_type}</span>
                </div>
                <p class="text-sm mt-2">${goal.description || ""}</p>
                
                <div class="progress-container mt-3">
                    <div class="flex-between text-xs mb-1">
                        <span>Progress: ${goal.current_value}/${goal.target_value}</span>
                        <span>${percentage}%</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill ${barColor}" style="width: ${percentage}%"></div>
                    </div>
                </div>
                
                ${goal.deadline ? `<p class="text-xs mt-2">Deadline: <strong>${utils.formatDate(goal.deadline)}</strong></p>` : ""}
                
                <div class="mt-3 flex gap-2">
                    <button class="btn btn-sm btn-outline" onclick="window.goalsHandler.showEditModal(${goal.id})">Update</button>
                    ${percentage < 100 ? `<button class="btn btn-sm btn-success" onclick="window.goalsHandler.quickIncrement(${goal.id}, ${goal.current_value}, 1)">+1</button>` : ""}
                </div>
            `;
            container.appendChild(card);
        });
    },

    async loadHierarchy() {
        try {
            const data = await api.get("/goals/hierarchy");
            const treeContainer = document.getElementById("goals-hierarchy");
            if (!treeContainer) return;

            // Basic recursive render. A real app might use a library like d3 or specialized css.
            treeContainer.innerHTML = "<pre>" + JSON.stringify(data, null, 2) + "</pre>";
        } catch (e) { }
    },

    async aiSuggest() {
        try {
            utils.showToast("AI analyzing your goals...", "info");
            const suggestions = await api.get("/goals/ai-suggest");
            const container = document.getElementById("goals-ai-panel");
            if (container && suggestions.length) {
                container.innerHTML = "<h4>AI Suggestions</h4><ul>" +
                    suggestions.map(s => `<li>${s}</li>`).join("") + "</ul>";
            }
        } catch (e) { }
    },

    async atRisk() {
        try {
            const risks = await api.get("/goals/at-risk");
            const container = document.getElementById("goals-risk-panel");
            if (container) {
                if (!risks.length) {
                    container.innerHTML = "<div class='alert alert-success'>All bounded goals are on pace.</div>";
                    return;
                }
                let html = "<div class='alert alert-warning'><h4>Goals At Risk</h4><ul>";
                risks.forEach(r => {
                    html += `<li><strong>${r.title}</strong>: Needs ${r.required_pace}/day, currently doing ${r.actual_pace}/day.</li>`;
                });
                html += "</ul></div>";
                container.innerHTML = html;
            }
        } catch (e) { }
    },

    async progressReport() {
        try {
            utils.showToast("Generating narrative...", "info");
            const report = await api.get("/goals/progress-report");
            alert("Progress Report:\n\n" + report); // Quick display for prototype
        } catch (e) { }
    },

    // Modal CRUD operations ...
    showAddModal() {
        document.getElementById("goal-title").value = "";
        utils.showModal("goal-modal");
    },

    hideModal() {
        utils.hideModal("goal-modal");
    },

    async createGoal() {
        const title = document.getElementById("goal-title")?.value;
        const target_value = document.getElementById("goal-target")?.value;
        const goal_type = document.getElementById("goal-type")?.value || "monthly";

        if (!title) return utils.showToast("Title required", "error");

        try {
            await api.post("/goals", {
                title,
                target_value: parseFloat(target_value) || 1,
                current_value: 0,
                goal_type
            });
            this.hideModal();
            this.loadGoals();
        } catch (e) { }
    },

    async quickIncrement(id, current, amount) {
        try {
            await api.put(`/goals/${id}`, { current_value: current + amount });
            this.loadGoals();
        } catch (e) { }
    }
};
