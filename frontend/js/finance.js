// finance.js — Expense & Budget Parsing

window.financeHandler = {
    async loadFinance() {
        this.loadSummary();
        this.loadTransactions();
        this.loadBudgetStatus();
    },

    async loadSummary() {
        try {
            const sumData = await api.get("/finance/summary?period=month");

            const incEl = document.getElementById("finance-income");
            const expEl = document.getElementById("finance-expenses");
            const savEl = document.getElementById("finance-savings");

            if (incEl) incEl.textContent = utils.formatCurrency(sumData.total_income || 0);
            if (expEl) expEl.textContent = utils.formatCurrency(sumData.total_expenses || 0);
            if (savEl) savEl.textContent = utils.formatCurrency(sumData.net_savings || 0);

            // Chart
            if (sumData.category_breakdown && sumData.category_breakdown.length > 0) {
                this.createPieChart(sumData.category_breakdown);
            } else {
                // Clear chart
                if (this.pieChart) this.pieChart.destroy();
            }
        } catch (e) { }
    },

    createPieChart(breakdown) {
        const ctx = document.getElementById('finance-category-chart');
        if (!ctx) return;

        if (this.pieChart) this.pieChart.destroy();

        const labels = breakdown.map(i => i.category);
        const data = breakdown.map(i => i.amount);

        if (window.Chart) {
            this.pieChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: [
                            '#EF4444', '#F59E0B', '#10B981', '#3B82F6', '#6366F1', '#8B5CF6', '#EC4899'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'right' }
                    }
                }
            });
        }
    },

    async loadTransactions(filters = "") {
        try {
            const txs = await api.get(`/finance/transactions${filters ? '?' + filters : ''}`);
            const list = document.getElementById("finance-transaction-list");
            if (!list) return;

            list.innerHTML = "";
            if (!txs || txs.length === 0) {
                list.innerHTML = "<p>No recent transactions.</p>";
                return;
            }

            // show last 10
            txs.slice(0, 10).forEach(t => {
                const isInc = t.type === "income";
                list.innerHTML += `
                    <div class="card flex-between mb-2">
                        <div>
                            <strong>${t.category}</strong> <br>
                            <small class="opacity-75">${t.description || "No note"}</small>
                        </div>
                        <div class="text-right">
                            <strong class="${isInc ? 'text-success' : 'text-danger'}">
                                ${isInc ? '+' : '-'}${utils.formatCurrency(t.amount)}
                            </strong><br>
                            <small class="text-xs">${utils.formatDate(t.date)}</small>
                        </div>
                    </div>
                `;
            });
        } catch (e) { }
    },

    async loadBudgetStatus() {
        try {
            const statusData = await api.get("/finance/budgets/status");
            const container = document.getElementById("finance-budget-bars");
            if (!container) return;

            container.innerHTML = "";
            if (!statusData || !statusData.length) {
                container.innerHTML = "<small>No active budgets.</small>";
                return;
            }

            statusData.forEach(b => {
                const perc = Math.min(100, Math.round(b.percentage_used));
                let colorClass = "bg-success";
                if (perc > 75) colorClass = "bg-warning";
                if (perc > 95) colorClass = "bg-danger";

                container.innerHTML += `
                    <div class="mb-3">
                        <div class="flex-between text-sm mb-1">
                            <span>${b.category}</span>
                            <span>${utils.formatCurrency(b.spent_amount)} / ${utils.formatCurrency(b.budget_amount)}</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill ${colorClass}" style="width: ${perc}%"></div>
                        </div>
                    </div>
                `;
            });
        } catch (e) { }
    },

    async aiParseTransaction() {
        const input = window.prompt("Paste receipt text or log naturally (e.g., 'Ate lunch for 15.50 today')");
        if (!input) return;

        utils.showLoading("finance-transaction-list");
        try {
            const parsed = await api.post("/finance/ai-parse", { text: input });
            if (parsed && parsed.amount) {
                if (confirm(`AI Parsed Transaction:\nAmount: ${parsed.amount}\nType: ${parsed.type}\nCategory: ${parsed.category}\nDesc: ${parsed.description}\n\nSave this?`)) {
                    await api.post("/finance/transactions", parsed);
                    this.loadFinance();
                    utils.showToast("Transaction saved", "success");
                } else {
                    utils.hideLoading("finance-transaction-list");
                }
            } else {
                utils.hideLoading("finance-transaction-list");
                utils.showToast("AI couldn't extract finance data.", "warning");
            }
        } catch (e) {
            utils.hideLoading("finance-transaction-list");
        }
    }
};
