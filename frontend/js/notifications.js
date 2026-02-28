// notifications.js — Global Alerts Polling & State Badges

window.notificationsHandler = {
    init() {
        this.requestPermission();
        this.pollInterval = setInterval(this.pollNotifications.bind(this), 5 * 60 * 1000);
        this.pollNotifications();

        const bell = document.getElementById("nav-bell");
        if (bell) bell.onclick = () => this.toggleDropdown();
    },

    async requestPermission() {
        if (!('Notification' in window)) return;
        if (Notification.permission === 'default') {
            await Notification.requestPermission();
        }
    },

    showNative(n) {
        if (Notification.permission === 'granted') {
            new Notification(n.title, {
                body: n.message,
                icon: 'https://ui-avatars.com/api/?name=JEXI&background=8B5CF6&color=fff'
            });
        }
    },

    async pollNotifications() {
        if (!api.isLoggedIn()) return;

        try {
            await api.get("/notifications/generate");
            const n = await api.get("/notifications?unread_only=true");

            // Check for really new ones to show a native alert
            if (n.length > 0) {
                const latest = n[0];
                const lastSeenId = utils.getFromLocal("last_notif_id");
                if (latest.id !== lastSeenId) {
                    this.showNative(latest);
                    utils.saveToLocal("last_notif_id", latest.id);
                }
            }

            this.updateBadge(n.length);
            this.renderDropdown(n);
        } catch (e) { }
    },

    updateBadge(count) {
        const badge = document.getElementById("nav-bell-badge");
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 9 ? "9+" : count;
                badge.style.display = "inline-flex";
            } else {
                badge.style.display = "none";
            }
        }
    },

    toggleDropdown() {
        const d = document.getElementById("notifications-dropdown");
        if (d) {
            d.style.display = d.style.display === "block" ? "none" : "block";
            if (d.style.display === "block") {
                this.pollNotifications(); // Reload immediately on open
            }
        }
    },

    renderDropdown(notifications) {
        const list = document.getElementById("notifications-list");
        if (!list) return;

        list.innerHTML = "";
        if (!notifications || notifications.length === 0) {
            list.innerHTML = "<div class='text-center p-3 text-sm opacity-50'>Clear horizon. No alerts.</div>";
            return;
        }

        const iconMap = {
            "reminder": "⏰", "warning": "⚠️", "streak": "🔥",
            "celebration": "🎉", "insight": "💡"
        };

        notifications.slice(0, 10).forEach(n => {
            const el = document.createElement("div");
            el.className = "notification-item hover-bg transition p-2 border-bottom flex gap-2 cursor-pointer";

            el.innerHTML = `
                <div class="text-xl">${iconMap[n.type] || "📌"}</div>
                <div>
                    <h5 class="text-sm m-0">${n.title}</h5>
                    <p class="text-xs m-0 opacity-75">${n.message}</p>
                    <small class="text-xs opacity-50 block mt-1">${utils.timeAgo(n.created_at)}</small>
                </div>
            `;

            el.onclick = () => this.markRead(n.id);
            list.appendChild(el);
        });
    },

    async markRead(id) {
        try {
            await api.put(`/notifications/${id}/read`);
            this.pollNotifications();
        } catch (e) { }
    }
};

// Global click to close dropdowns
document.addEventListener("click", (e) => {
    const d = document.getElementById("notifications-dropdown");
    const b = document.getElementById("nav-bell");
    if (d && d.style.display === "block" && !d.contains(e.target) && (!b || !b.contains(e.target))) {
        d.style.display = "none";
    }
});
