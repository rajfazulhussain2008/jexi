// analytics.js — Macro Daily Life Score Visualizations

window.analyticsHandler = {
    async loadAnalytics() {
        this.loadLifeScore();
        this.loadLifeScoreHistory();
        this.loadAIInsights();
    },

    async loadLifeScore() {
        try {
            utils.showToast("Compiling macro aggregates...", "info");
            const data = await api.get("/analytics/life-score");

            if (data && data.total !== undefined) {
                document.getElementById("analytics-score-text").textContent = Math.round(data.total);
                this.renderLifeScoreDoughnut(data.total);

                // Breakdowns
                if (data.breakdown) {
                    const c = document.getElementById("analytics-breakdown-bars");
                    if (c) {
                        c.innerHTML = "";
                        const colors = {
                            "tasks": "bg-primary",
                            "habits": "bg-accent",
                            "health": "bg-success",
                            "goals": "bg-warning",
                            "coding": "bg-danger"
                        };

                        for (const [k, v] of Object.entries(data.breakdown)) {
                            // Each category out of 20
                            const perc = (v / 20) * 100;
                            c.innerHTML += `
                                <div class="mb-2">
                                    <div class="flex-between text-xs mb-1">
                                        <span style="text-transform: capitalize;">${k}</span>
                                        <span>${v}/20</span>
                                    </div>
                                    <div class="progress-bar-bg">
                                        <div class="progress-bar-fill ${colors[k]}" style="width: ${perc}%"></div>
                                    </div>
                                </div>
                            `;
                        }
                    }
                }
            }
        } catch (e) { }
    },

    renderLifeScoreDoughnut(score) {
        const ctx = document.getElementById('analytics-score-chart');
        if (!ctx) return;

        if (this.mainChart) this.mainChart.destroy();

        const remaining = Math.max(0, 100 - score);
        const color = score > 80 ? '#10B981' : (score > 50 ? '#F59E0B' : '#EF4444');

        if (window.Chart) {
            this.mainChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    datasets: [{
                        data: [score, remaining],
                        backgroundColor: [color, 'rgba(255, 255, 255, 0.05)'],
                        borderWidth: 0,
                    }]
                },
                options: {
                    circumference: 360,
                    cutout: '85%',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { tooltip: { enabled: false } },
                    animation: { animateRotate: true, animateScale: true }
                }
            });
        }
    },

    async loadLifeScoreHistory() {
        const ctx = document.getElementById('analytics-history-chart');
        if (!ctx) return;

        try {
            const hist = await api.get("/analytics/life-score/history?period=30");
            if (!hist || !hist.length) return;

            if (this.histChart) this.histChart.destroy();

            const labels = hist.map(d => utils.formatDate(d.date).slice(0, 5));
            const data = hist.map(d => d.total_score);

            if (window.Chart) {
                this.histChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Daily Score',
                            data: data,
                            borderColor: '#3B82F6',
                            tension: 0.3,
                            fill: true,
                            backgroundColor: 'rgba(59, 130, 246, 0.1)'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: { y: { min: 0, max: 100 } }
                    }
                });
            }
        } catch (e) { }
    },

    async loadAIInsights() {
        const pan = document.getElementById("analytics-ai-panel");
        if (!pan) return;

        try {
            utils.showToast("Synthesizing correlations...", "info");
            const insights = await api.get("/analytics/ai-insights");

            pan.innerHTML = "<h4>Macro Analysis</h4>";
            if (!insights || !insights.length) {
                pan.innerHTML += "<p>More data required to establish confidence intervals.</p>";
                return;
            }

            insights.forEach(i => {
                pan.innerHTML += `<div class="alert alert-info border-left mb-2 text-sm">${i}</div>`;
            });
        } catch (e) {
            pan.innerHTML = "<p>Data aggregation unready.</p>";
        }
    },

    async generateWeeklyReview() {
        utils.showToast("Generating Weekly Deep Dive...", "info");
        try {
            const r = await api.post("/analytics/weekly-review");
            alert("Weekly Review:\n\n" + r);
        } catch (e) { }
    }
};
