// projects.js — Kanban, GitHub workflows, AI readme generations

window.projectsHandler = {
    async loadProjects() {
        try {
            utils.showLoading("projects-list");
            const projects = await api.get("/projects");
            this.renderProjects(projects);
            utils.hideLoading("projects-list");
        } catch (e) {
            utils.hideLoading("projects-list");
        }
    },

    renderProjects(projects) {
        const c = document.getElementById("projects-list");
        if (!c) return;

        c.innerHTML = "";
        if (!projects || projects.length === 0) {
            c.innerHTML = "<p class='empty-state'>No active projects.</p>";
            return;
        }

        projects.forEach(p => {
            const card = document.createElement("div");
            card.className = "card mb-3 hover-scale fade-in";

            let techHTML = "";
            try {
                const stack = JSON.parse(p.tech_stack);
                stack.forEach(t => techHTML += `<span class="badge" style="margin-right:4px;">${t}</span>`);
            } catch (e) { }

            card.innerHTML = `
                <div class="flex-between">
                    <h3 class="m-0">${p.name}</h3>
                    <span class="badge ${p.status === 'completed' ? 'badge-success' : 'badge-primary'}">${p.status}</span>
                </div>
                <p class="text-sm opacity-75 mt-2">${p.description || "No description provided."}</p>
                <div class="mt-2">${techHTML}</div>
                <div class="mt-3 flex gap-2">
                    <button class="btn btn-outline btn-sm" onclick="window.projectsHandler.loadKanban(${p.id}, '${p.name}')">Board</button>
                    ${p.github_url ? `<a href="${p.github_url}" target="_blank" class="btn btn-ghost btn-sm">GitHub</a>` : ""}
                    <button class="btn btn-ghost btn-sm" onclick="window.projectsHandler.generateReadme(${p.id})">README</button>
                    <button class="btn btn-ghost btn-danger btn-sm" title="Delete" onclick="window.projectsHandler.deleteProject(${p.id})">🗑️</button>
                </div>
            `;
            c.appendChild(card);
        });
    },

    async createProject() {
        const name = document.getElementById("proj-name")?.value;
        const desc = document.getElementById("proj-desc")?.value;
        const stack = document.getElementById("proj-stack")?.value; // comma sorted

        if (!name) return;

        try {
            const techArr = stack ? stack.split(",").map(s => s.trim()) : [];
            await api.post("/projects", { name, description: desc, tech_stack: techArr });
            utils.hideModal("project-modal");
            this.loadProjects();
        } catch (e) { }
    },

    async deleteProject(id) {
        if (!confirm("Are you sure? This deletes all associated tasks!")) return;
        try {
            await api.del(`/projects/${id}`);
            this.loadProjects();
        } catch (e) { }
    },

    // KANBAN LOGIC

    async loadKanban(id, name) {
        try {
            document.getElementById("kanban-project-title").textContent = `Board: ${name}`;
            document.getElementById("projects-main-view").style.display = "none";
            document.getElementById("projects-kanban-view").style.display = "block";

            utils.showToast("Loading Board...", "info");
            const board = await api.get(`/projects/${id}/board`);

            this.renderKanbanColumn("todo", "To Do", board.todo || []);
            this.renderKanbanColumn("in_progress", "In Progress", board.in_progress || []);
            this.renderKanbanColumn("review", "Review", board.review || []);
            this.renderKanbanColumn("done", "Done", board.done || []);

            // Set current working ID for drag logic API
            window._currentKanbanProjectId = id;

        } catch (e) {
            utils.showToast("Failed to load Kanban board", "error");
        }
    },

    backToProjects() {
        document.getElementById("projects-kanban-view").style.display = "none";
        document.getElementById("projects-main-view").style.display = "block";
        this.loadProjects();
    },

    renderKanbanColumn(id, title, tasks) {
        const col = document.getElementById(`kanban-${id}`);
        if (!col) return;

        col.innerHTML = `<h4 class="kanban-col-header text-center mb-3">${title} (${tasks.length})</h4>`;

        const dragArea = document.createElement("div");
        dragArea.className = "kanban-drag-area";
        dragArea.dataset.status = id;

        dragArea.ondragover = (e) => e.preventDefault();
        dragArea.ondrop = (e) => this.handleKanbanDrop(e, id);

        tasks.forEach(t => {
            const card = document.createElement("div");
            card.className = "kanban-card";
            card.draggable = true;
            card.dataset.taskId = t.id;

            card.ondragstart = (e) => {
                e.dataTransfer.setData("text/plain", t.id);
            };

            card.innerHTML = `
                <div class="text-xs opacity-75 mb-1">${t.category || 'Task'}</div>
                <strong>${t.title}</strong>
            `;
            dragArea.appendChild(card);
        });

        col.appendChild(dragArea);
    },

    async handleKanbanDrop(e, newStatus) {
        e.preventDefault();
        const taskId = e.dataTransfer.getData("text/plain");
        const projectId = window._currentKanbanProjectId;

        if (!taskId || !projectId) return;

        try {
            // Optimistic UI update could go here, but reload is safer currently
            await api.put(`/projects/${projectId}/tasks/${taskId}/move`, { status: newStatus });

            // Re-render board
            const name = document.getElementById("kanban-project-title").textContent.replace("Board: ", "");
            this.loadKanban(projectId, name);
        } catch (err) { }
    },

    // AI Generation
    async generateReadme(id) {
        utils.showToast("Generating comprehensive README...", "info");
        try {
            const readme = await api.post(`/projects/${id}/generate-readme`, {});

            const mb = document.getElementById("project-ai-modal-body");
            if (mb) {
                mb.innerHTML = `<button class="btn btn-sm btn-outline mb-2" onclick="navigator.clipboard.writeText(this.nextElementSibling.innerText)">Copy raw markup</button> <pre style="white-space:pre-wrap; font-size:12px;">${readme.replace(/</g, "&lt;")}</pre>`;
                utils.showModal("project-ai-modal");
            }
        } catch (e) { }
    },

    async aiKickstart() {
        const idea = prompt("What's the core idea of your new application?");
        if (!idea) return;

        utils.showLoading("projects-list");
        try {
            const bp = await api.post("/dev/kickstart", {
                idea, languages: ["Python", "JS"], time_per_day: 2
            });
            utils.hideLoading("projects-list");

            let html = `<h4>AI Prototype Blueprint</h4>`;
            html += `<p><strong>Stack:</strong> ${bp.tech_stack?.join(", ")}</p>`;
            html += `<p><strong>Timeline:</strong> ~${bp.timeline_days} days</p>`;
            html += `<h5>Priority Features:</h5><ul>`;
            (bp.features?.P0 || []).forEach(f => html += `<li>${f}</li>`);
            html += `</ul>`;

            const c = document.getElementById("project-ai-modal-body");
            if (c) {
                c.innerHTML = html;
                utils.showModal("project-ai-modal");
            }
        } catch (e) {
            utils.hideLoading("projects-list");
        }
    },

    showAddModal() { utils.showModal("project-modal"); },
    hideModal() { utils.hideModal("project-modal"); utils.hideModal("project-ai-modal"); }
};
