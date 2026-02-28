// tasks.js — Task Management Engine

window.tasksHandler = {
    async loadTasks() {
        try {
            utils.showLoading("tasks-container");
            // get filters from UI
            const statusFilter = document.getElementById("task-filter-status")?.value || "";
            const categoryFilter = document.getElementById("task-filter-category")?.value || "";

            let queryUrl = "/tasks";
            let params = [];
            if (statusFilter) params.push(`status=${statusFilter}`);
            if (categoryFilter) params.push(`category=${categoryFilter}`);
            if (params.length) queryUrl += "?" + params.join("&");

            const tasks = await api.get(queryUrl);
            utils.hideLoading("tasks-container");
            this.renderTasks(tasks);
            this.loadStats();
        } catch (e) {
            utils.hideLoading("tasks-container");
            document.getElementById("tasks-container").innerHTML = "<p class='error'>Failed to load tasks.</p>";
        }
    },

    renderTasks(tasks) {
        const container = document.getElementById("tasks-container");
        if (!container) return;

        container.innerHTML = "";
        if (!tasks || tasks.length === 0) {
            container.innerHTML = "<p class='empty-state'>No tasks found. Create your first task!</p>";
            return;
        }

        tasks.forEach(task => {
            const card = document.createElement("div");
            card.className = "task-card " + (task.status === "done" ? "task-done" : "");

            const prioClass = `task-prio-${task.priority || "medium"}`;

            card.innerHTML = `
                <div class="task-prio-bar ${prioClass}"></div>
                <div class="task-checkbox" onclick="window.tasksHandler.toggleTask(${task.id}, '${task.status}')">
                    ${task.status === "done" ? "✅" : "⬜"}
                </div>
                <div class="task-content">
                    <h4>${utils.markdownToHtml(task.title)}</h4>
                    ${task.due_date ? `<small>⏳ ${utils.formatDate(task.due_date)}</small>` : ""}
                    ${task.category ? `<span class="badge badge-accent">${task.category}</span>` : ""}
                </div>
                <div class="task-actions">
                    <button class="btn btn-sm btn-ghost" onclick="window.tasksHandler.showEditModal(${task.id})">✏️</button>
                    <button class="btn btn-sm btn-ghost btn-danger" onclick="window.tasksHandler.deleteTask(${task.id})">🗑️</button>
                </div>
            `;
            container.appendChild(card);
        });
    },

    async loadStats() {
        const statsBar = document.getElementById("tasks-stats");
        if (!statsBar) return;
        try {
            const stats = await api.get("/tasks/stats");
            statsBar.innerHTML = `
                <span>Total: ${stats.total || 0}</span> | 
                <span class="text-success">Done: ${stats.completed || 0}</span> | 
                <span class="text-warning">Pending: ${stats.pending || 0}</span> | 
                <span class="text-danger">Overdue: ${stats.overdue || 0}</span>
            `;
        } catch (e) {
            statsBar.innerHTML = "Stats unavailable";
        }
    },

    async createTask() {
        const title = document.getElementById("task-title-input")?.value;
        const priority = document.getElementById("task-priority-input")?.value || "medium";
        const category = document.getElementById("task-category-input")?.value || "";
        const due_date = document.getElementById("task-due-input")?.value || null;

        if (!title) return utils.showToast("Title is required", "error");

        try {
            await api.post("/tasks", { title, priority, category, due_date });
            utils.hideModal("task-modal");
            this.loadTasks();
            utils.showToast("Task created", "success");
        } catch (e) {
            // Error managed in api.js
        }
    },

    async updateTask(id) {
        const title = document.getElementById("task-edit-title-input")?.value;
        const priority = document.getElementById("task-edit-priority-input")?.value || "medium";
        const status = document.getElementById("task-edit-status-input")?.value || "pending";
        try {
            await api.put(`/tasks/${id}`, { title, priority, status });
            utils.hideModal("task-edit-modal");
            this.loadTasks();
            utils.showToast("Task updated", "success");
        } catch (e) { }
    },

    async deleteTask(id) {
        if (!confirm("Delete this task?")) return;
        try {
            await api.del(`/tasks/${id}`);
            this.loadTasks();
            utils.showToast("Task deleted", "info");
        } catch (e) { }
    },

    async toggleTask(id, currentStatus) {
        const newStatus = currentStatus === "done" ? "pending" : "done";
        try {
            await api.put(`/tasks/${id}`, { status: newStatus });
            this.loadTasks();
            if (newStatus === "done") utils.showToast("Task completed!", "success");
        } catch (e) { }
    },

    async aiCreate() {
        const input = window.prompt("Describe your task naturally (e.g. 'Remind me to call John tomorrow morning about the invoice')");
        if (!input) return;

        utils.showLoading("tasks-container");
        try {
            const parsed = await api.post("/tasks/ai-create", { text: input });
            utils.hideLoading("tasks-container");

            if (parsed && parsed.title) {
                if (confirm(`AI Parsed Task:\nTitle: ${parsed.title}\nDue: ${parsed.due_date || 'None'}\nPriority: ${parsed.priority}\n\nCreate this?`)) {
                    await api.post("/tasks", parsed);
                    this.loadTasks();
                    utils.showToast("AI task created", "success");
                }
            } else {
                utils.showToast("AI couldn't parse task", "warning");
            }
        } catch (e) {
            utils.hideLoading("tasks-container");
        }
    },

    async aiBreakdown(taskId) {
        // Assume modal or context menu triggers this
        try {
            const task = await api.get(`/tasks/${taskId}`);
            if (!task) return;

            utils.showToast("Breaking down task...", "info");
            const breakdown = await api.post("/tasks/ai-breakdown", { text: task.title });

            if (breakdown && breakdown.length) {
                let txt = "AI Suggested Subtasks:\n";
                breakdown.forEach(s => txt += `- ${s.title} (${s.estimated_minutes}m)\n`);
                if (confirm(txt + "\nAdd these to task?")) {
                    await api.put(`/tasks/${taskId}`, { subtasks: breakdown });
                    this.loadTasks();
                }
            } else {
                utils.showToast("No subtasks generated", "info");
            }
        } catch (e) { }
    },

    // Modal helpers
    showAddModal() {
        document.getElementById("task-title-input").value = "";
        utils.showModal("task-modal");
    },

    async showEditModal(id) {
        try {
            const task = await api.get(`/tasks/${id}`);
            document.getElementById("task-edit-id").value = task.id;
            document.getElementById("task-edit-title-input").value = task.title;
            document.getElementById("task-edit-priority-input").value = task.priority;
            document.getElementById("task-edit-status-input").value = task.status;
            utils.showModal("task-edit-modal");
        } catch (e) { }
    },

    hideModal() {
        utils.hideModal('task-modal');
        utils.hideModal('task-edit-modal');
    },

    applyFilters() {
        this.loadTasks();
    }
};
