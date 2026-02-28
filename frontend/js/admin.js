// admin.js — Administrator Tools (User Management)

window.adminHandler = {
    init() {
        this.loadUsers();
        this.setupEventListeners();
    },

    setupEventListeners() {
        const form = document.getElementById("adminAddUserForm");
        if (form) {
            form.onsubmit = (e) => this.handleAddUser(e);
        }
    },

    async loadUsers() {
        const container = document.getElementById("adminUserList");
        if (!container) return;

        try {
            utils.showLoading("adminUserList");
            const users = await api.get("/admin/users");
            utils.hideLoading("adminUserList");

            container.innerHTML = "";
            users.forEach(u => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td>${u.id}</td>
                    <td><strong>${u.username}</strong></td>
                    <td><span class="badge ${u.is_admin ? 'badge-primary' : 'badge-ghost'}">${u.is_admin ? 'Admin' : 'Friend'}</span></td>
                    <td>
                        <button class="btn btn-sm btn-ghost text-red" onclick="adminHandler.deleteUser(${u.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                `;
                container.appendChild(tr);
            });
        } catch (e) {
            utils.hideLoading("adminUserList");
            container.innerHTML = "<tr><td colspan='4'>Failed to load users.</td></tr>";
        }
    },

    async handleAddUser(e) {
        e.preventDefault();
        const username = document.getElementById("adminNewUsername").value;
        const password = document.getElementById("adminNewPassword").value;

        if (!username || !password) return;

        try {
            const res = await api.post("/admin/users", { username, password });
            if (res.status === "success") {
                utils.showToast(res.message, "success");
                document.getElementById("adminAddUserForm").reset();
                this.loadUsers();

                // Also reload friends so they appear in sidebar/chat
                if (window.socialHandler) {
                    window.socialHandler.loadFriends();
                }
            }
        } catch (err) {
            // Toast handled by api.js
        }
    },

    async deleteUser(id) {
        if (!confirm("Are you sure you want to delete this user? This cannot be undone.")) return;

        try {
            // Endpoint not yet implemented in backend, but adding for future
            // await api.del(`/admin/users/${id}`);
            utils.showToast("Delete functionality coming soon.", "info");
        } catch (e) { }
    }
};
