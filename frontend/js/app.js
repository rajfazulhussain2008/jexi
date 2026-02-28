// app.js — Main Application Controller

const app = {
    init() {
        this.setupTheme();

        if (!api.isLoggedIn()) {
            this.showLoginScreen();
            return;
        }

        this.showMainApp();
        this.setupNavHandlers();

        // Initial view
        this.switchView('dashboardView', 0);

        // Initialize notifications polling
        if (window.notificationsHandler) {
            window.notificationsHandler.init();
        }

        // Register Service Worker for Offline/Android App feel
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
                .then(() => console.log("JEXI Service Worker Registered"))
                .catch(err => console.error("SW Registration failed:", err));
        }

        // Online/Offline Status Listeners
        window.addEventListener('online', () => utils.updateSyncStatus("online"));
        window.addEventListener('offline', () => utils.updateSyncStatus("offline"));
        utils.updateSyncStatus(navigator.onLine ? "online" : "offline");
    },

    showLoginScreen() {
        const loginScreen = document.getElementById("loginScreen");
        const mainApp = document.getElementById("mainApp");
        if (loginScreen) loginScreen.classList.remove("hidden");
        if (mainApp) mainApp.classList.add("hidden");
        // Token is only cleared on explicit logout, not here
    },

    showMainApp() {
        const loginScreen = document.getElementById("loginScreen");
        const mainApp = document.getElementById("mainApp");
        if (loginScreen) loginScreen.classList.add("hidden");
        if (mainApp) mainApp.classList.remove("hidden");

        // Check for admin status to show admin menu
        if (api.isAdmin()) {
            document.querySelectorAll(".admin-only").forEach(el => el.classList.remove("hidden"));
        } else {
            document.querySelectorAll(".admin-only").forEach(el => el.classList.add("hidden"));
        }
    },

    setupNavHandlers() {
        const navLinks = document.querySelectorAll(".sidebar .nav-item");
        navLinks.forEach((link, index) => {
            link.addEventListener("click", (e) => {
                e.preventDefault();
                const viewId = link.getAttribute("data-target");
                this.switchView(viewId, index);

                // On mobile, close sidebar after clicking
                if (window.innerWidth <= 900) {
                    this.toggleSidebar(false);
                }
            });
        });

        const btnOpen = document.getElementById("sidebarOpenBtn");
        if (btnOpen) {
            btnOpen.addEventListener("click", () => this.toggleSidebar(true));
        }

        const btnClose = document.getElementById("sidebarCloseBtn");
        if (btnClose) {
            btnClose.addEventListener("click", () => this.toggleSidebar(false));
        }

        // Keep backwards compatibility just in case
        const hamburger = document.getElementById("mobile-menu-btn");
        if (hamburger) {
            hamburger.addEventListener("click", () => this.toggleSidebar());
        }

        // Logout button
        const logoutBtn = document.getElementById("logoutBtn");
        if (logoutBtn) {
            logoutBtn.addEventListener("click", () => {
                localStorage.removeItem("jexi_token");
                localStorage.removeItem("jexi_is_admin");
                utils.showToast("Logged out successfully", "success");
                setTimeout(() => window.location.reload(), 800);
            });
        }
    },

    switchView(viewId, navIndex) {
        // Update Nav Actives
        const navLinks = document.querySelectorAll(".sidebar .nav-item");
        navLinks.forEach((l, idx) => {
            if (idx === navIndex) l.classList.add("active");
            else l.classList.remove("active");
        });

        // Hide all views
        const views = document.querySelectorAll(".view");
        views.forEach(v => v.style.display = "none");

        // Show target view
        const targetView = document.getElementById(viewId);
        if (targetView) targetView.style.display = "block";

        // Clean up intervals from previous views
        if (window.socialHandler && typeof window.socialHandler.cleanup === 'function') {
            window.socialHandler.cleanup();
        }

        // Route to specific controllers safely
        try {
            switch (viewId) {
                case 'dashboardView': this.loadDashboard(); break;
                case 'chatView': if (window.chatHandler) window.chatHandler.initChat(); break;
                case 'tasksView': if (window.tasksHandler) window.tasksHandler.loadTasks(); break;
                case 'goalsView': if (window.goalsHandler) window.goalsHandler.loadGoals(); break;
                case 'habitsView': if (window.habitsHandler) window.habitsHandler.loadHabits(); break;
                case 'journalView': if (window.journalHandler) window.journalHandler.loadJournal(); break;
                case 'financeView': if (window.financeHandler) window.financeHandler.loadFinance(); break;
                case 'healthView': if (window.healthHandler) window.healthHandler.loadHealth(); break;
                case 'devView': if (window.devHandler) window.devHandler.initDev(); break;
                case 'projectsView': if (window.projectsHandler) window.projectsHandler.loadProjects(); break;
                case 'learningView': if (window.learningHandler) window.learningHandler.init(); break;
                case 'analyticsView': if (window.analyticsHandler) window.analyticsHandler.loadAnalytics(); break;
                case 'plannerView': if (window.plannerHandler) window.plannerHandler.loadPlanner(); break;
                case 'settingsView': if (window.settingsHandler) window.settingsHandler.loadSettings(); break;
                case 'adminView': if (window.adminHandler) window.adminHandler.init(); break;
                case 'communityView': break; // Placeholder
                case 'friendsView': if (window.socialHandler) window.socialHandler.loadFriends(); break;
            }
        } catch (e) {
            console.error(`Error loading view [${viewId}]:`, e);
            utils.showToast(`Error handling view: ${viewId}`, "error");
        }
    },

    async handleLoginAndSetup(e) {
        e.preventDefault();
        const user = document.getElementById("usernameInput").value.trim();
        const pass = document.getElementById("passwordInput").value;

        if (!user || !pass) {
            utils.showToast("Please enter username and password", "warning");
            return;
        }

        const goToApp = () => {
            this.showMainApp();
            this.setupNavHandlers();
            this.switchView('dashboardView', 0);
        };

        try {
            await api.login(user, pass);
            goToApp();
        } catch (loginErr) {
            utils.showToast("Login failed. Check your username and password.", "error");
        }
    },

    async loadDashboard() {
        try {
            const data = await api.get("/analytics/dashboard");
            if (!data) return;

            // Populate dashboard elements
            const lsText = document.getElementById("dash-life-score-text");
            if (lsText && data.life_score) {
                lsText.textContent = data.life_score.total;
                this.renderLifeScoreChart(data.life_score.total);
            }

            const activeProj = document.getElementById("dash-projects-count");
            if (activeProj) activeProj.textContent = data.active_projects || 0;

            const tasksCount = document.getElementById("dash-tasks-count");
            if (tasksCount && data.tasks_today) {
                tasksCount.textContent = `${data.tasks_today.done}/${data.tasks_today.pending + data.tasks_today.done}`;
            }

            const habitsCount = document.getElementById("dash-habits-count");
            if (habitsCount) habitsCount.textContent = data.habits_done_today || 0;

        } catch (e) {
            console.error("Dashboard error", e);
        }
    },

    renderLifeScoreChart(score) {
        const ctx = document.getElementById('dash-life-score-chart');
        if (!ctx) return;

        if (this.lifeChartInstance) {
            this.lifeChartInstance.destroy();
        }

        const remaining = Math.max(0, 100 - score);
        const color = score > 80 ? '#10B981' : (score > 50 ? '#F59E0B' : '#EF4444');

        if (window.Chart) {
            this.lifeChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    datasets: [{
                        data: [score, remaining],
                        backgroundColor: [color, 'rgba(255, 255, 255, 0.1)'],
                        borderWidth: 0,
                    }]
                },
                options: {
                    cutout: '80%',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { tooltip: { enabled: false } },
                    animation: { animateRotate: true }
                }
            });
        }
    },

    setupTheme() {
        // Force light theme
        const theme = "light";
        this.setTheme(theme);
    },

    setTheme(theme) {
        if (theme === "light") {
            document.body.classList.add("light-theme");
        } else {
            document.body.classList.remove("light-theme");
        }
        utils.saveToLocal("jexi_theme", theme);
    },

    toggleSidebar(forceState = null) {
        const sidebar = document.querySelector(".sidebar");
        if (!sidebar) return;

        let overlay = document.querySelector(".sidebar-overlay");
        if (!overlay) {
            overlay = document.createElement("div");
            overlay.className = "sidebar-overlay";
            document.body.appendChild(overlay);
            overlay.addEventListener("click", () => this.toggleSidebar(false));
        }

        const isActive = forceState !== null ? forceState : !sidebar.classList.contains("active");

        if (isActive) {
            sidebar.classList.add("active");
            overlay.classList.add("active");
        } else {
            sidebar.classList.remove("active");
            overlay.classList.remove("active");
        }
    }
};

// Start application
document.addEventListener("DOMContentLoaded", () => {
    // Bind global logins forms
    const loginForm = document.getElementById("loginForm");

    if (loginForm) {
        loginForm.addEventListener("submit", (e) => app.handleLoginAndSetup(e));
    }

    app.init();
});
