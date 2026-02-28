// health.js — Biometric and Mood Correlations

window.healthHandler = {
    async loadHealth() {
        this.loadScore();
        this.loadTodayLog();
        this.loadTrends();
    },

    async loadScore() {
        try {
            const data = await api.get("/health/score");
            const scoreEl = document.getElementById("health-score-text");
            if (scoreEl && data.total !== undefined) {
                scoreEl.textContent = data.total;
                this.createHealthGauge(data.total);
            }
        } catch (e) { }
    },

    createHealthGauge(score) {
        const ctx = document.getElementById('health-gauge-chart');
        if (!ctx) return;

        if (this.gaugeChart) this.gaugeChart.destroy();

        const remaining = Math.max(0, 100 - score);
        const color = score > 80 ? '#10B981' : (score > 50 ? '#F59E0B' : '#EF4444');

        if (window.Chart) {
            this.gaugeChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    datasets: [{
                        data: [score, remaining],
                        backgroundColor: [color, 'rgba(255, 255, 255, 0.1)'],
                        borderWidth: 0,
                    }]
                },
                options: {
                    rotation: 270, // Start from top
                    circumference: 180, // Half circle
                    cutout: '80%',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { tooltip: { enabled: false } },
                    animation: { animateRotate: true }
                }
            });
        }
    },

    async loadTodayLog() {
        try {
            const l = await api.get("/health/today");
            if (l) {
                document.getElementById("health-sleep").value = l.sleep_hours || "";
                document.getElementById("health-water").value = l.water_liters || "";
                document.getElementById("health-exercise").value = l.exercise_duration || "";
                document.getElementById("health-meals").value = l.meals_logged || "";
            }
        } catch (e) { }
    },

    async saveHealthLog() {
        const sleep_hours = parseFloat(document.getElementById("health-sleep").value);
        const water_liters = parseFloat(document.getElementById("health-water").value);
        const exercise_duration = parseInt(document.getElementById("health-exercise").value, 10);
        const meals_logged = parseInt(document.getElementById("health-meals").value, 10);

        try {
            await api.post("/health/log", {
                sleep_hours, water_liters, exercise_duration, meals_logged
            });
            utils.showToast("Health metrics updated", "success");
            this.loadScore(); // Update dial
        } catch (e) { }
    },

    async loadTrends() {
        const ctx = document.getElementById('health-trends-chart');
        if (!ctx) return;

        try {
            // Simplified multi-line fetch
            const [sleep, exercise] = await Promise.all([
                api.get("/health/trends?metric=sleep_hours"),
                api.get("/health/trends?metric=exercise_duration")
            ]);

            if (this.trendsChart) this.trendsChart.destroy();

            // Assume aligned dates for simplicity
            const labels = sleep.map(d => utils.formatDate(d.date).slice(0, 6));

            if (window.Chart) {
                this.trendsChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: 'Sleep (hrs)',
                                data: sleep.map(d => d.value),
                                borderColor: '#8B5CF6',
                                yAxisID: 'y',
                            },
                            {
                                label: 'Exercise (mins)',
                                data: exercise.map(d => d.value),
                                borderColor: '#10B981',
                                yAxisID: 'y1',
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: { mode: 'index', intersect: false },
                        scales: {
                            y: { type: 'linear', display: true, position: 'left' },
                            y1: { type: 'linear', display: true, position: 'right', grid: { drawOnChartArea: false } }
                        }
                    }
                });
            }
        } catch (e) { }
    },

    async loadAIInsights() {
        try {
            utils.showToast("Analyzing health patterns...", "info");
            const text = await api.get("/health/ai-insights");
            const panel = document.getElementById("health-ai-panel");
            if (panel) {
                panel.innerHTML = `<div class="alert alert-info border-left">${utils.markdownToHtml(text)}</div>`;
            }
        } catch (e) { }
    }
};
