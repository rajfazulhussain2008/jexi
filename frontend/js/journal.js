// journal.js — Self Reflection & NLP Journaling

window.journalHandler = {
    async loadJournal() {
        this.loadTodayEntry();
        this.loadPrompts();
        this.loadMoodTrends();
    },

    async loadTodayEntry() {
        try {
            utils.showLoading("journal-editor-col");
            const entry = await api.get("/journal/today");

            if (entry) {
                // Populate existing
                document.getElementById("journal-mood").value = entry.mood_score || 8;
                document.getElementById("journal-energy").value = entry.energy_score || 7;
                document.getElementById("journal-content").value = entry.content || "";
                document.getElementById("journal-gratitude").value = entry.gratitude || "";
                document.getElementById("journal-wins").value = entry.wins || "";
                document.getElementById("journal-challenges").value = entry.challenges || "";
            }
            this.updateMoodDisplay();
            utils.hideLoading("journal-editor-col");
        } catch (e) {
            utils.hideLoading("journal-editor-col");
        }
    },

    updateMoodDisplay() {
        const m = parseInt(document.getElementById("journal-mood")?.value || 8);
        const e = parseInt(document.getElementById("journal-energy")?.value || 7);

        const moodEmojis = ["😭", "😢", "😞", "🙁", "😐", "🙂", "😊", "😄", "😁", "🤩"];
        const moodEl = document.getElementById("moodDisp");
        if (moodEl) moodEl.textContent = `${moodEmojis[m - 1] || "😐"} (${m}/10)`;

        const energyEl = document.getElementById("energyDisp");
        if (energyEl) energyEl.textContent = `⚡ (${e}/10)`;
    },

    async saveEntry() {
        const mood_score = parseInt(document.getElementById("journal-mood").value);
        const energy_score = parseInt(document.getElementById("journal-energy").value);
        const content = document.getElementById("journal-content").value;
        const gratitude = document.getElementById("journal-gratitude").value;
        const wins = document.getElementById("journal-wins").value;
        const challenges = document.getElementById("journal-challenges").value;

        if (!content && !gratitude && !wins) return utils.showToast("Cannot save empty journal", "warning");

        try {
            await api.post("/journal/log", {
                mood_score, energy_score, content, gratitude, wins, challenges
            });
            utils.showToast("Journal saved successfully.", "success");
            this.loadMoodTrends(); // Refresh charts
        } catch (err) { }
    },

    async aiAnalyzeEntry() {
        const content = document.getElementById("journal-content").value;
        if (!content || content.length < 20) return utils.showToast("Not enough text to analyze!", "warning");

        utils.showToast("JEXI is analyzing your thoughts...", "info");
        try {
            const analysis = await api.post("/journal/analyze", { text: content });

            // Show modal with results
            const c = document.getElementById("genericModal");
            if (c) {
                c.querySelector(".modal-title").textContent = "AI Analysis";
                c.querySelector(".modal-body").innerHTML = `
                    <p><strong>Sentiment:</strong> ${analysis.sentiment || "Neutral"}</p>
                    <p><strong>Primary Emotion:</strong> ${analysis.emotion || "Calm"}</p>
                    <p><strong>Cognitive Distortions Detected:</strong> ${analysis.distortions?.join(", ") || "None"}</p>
                    <div class="alert alert-info mt-2"><strong>JEXI Perspective:</strong><br>${analysis.feedback}</div>
                `;
                utils.showModal("genericModal");
            }
        } catch (e) { }
    },

    async loadPrompts() {
        try {
            const list = document.getElementById("journal-prompts-list");
            if (!list) return;

            // Mocking local prompts if API is not fully hooked
            const prompts = [
                "What did you learn about yourself today?",
                "What is draining your energy right now?",
                "Describe a moment you felt proud today.",
                "How did you handle stress today?",
                "What can you do better tomorrow?"
            ];

            list.innerHTML = "";
            prompts.sort(() => 0.5 - Math.random()).slice(0, 3).forEach(p => {
                const li = document.createElement("li");
                li.className = "cursor-pointer hover-text-accent";
                li.textContent = p;
                li.onclick = () => {
                    const box = document.getElementById("journal-content");
                    if (box) box.value += (box.value ? "\n\n" : "") + `**${p}**\n\n`;
                };
                list.appendChild(li);
            });
        } catch (e) { }
    },

    async loadMoodTrends() {
        const ctx = document.getElementById('moodChart');
        if (!ctx) return;

        try {
            const hist = await api.get("/journal/history?days=14");
            if (!hist || hist.length === 0) return;

            if (this.chart) this.chart.destroy();

            const labels = hist.map(d => utils.formatDate(d.date).slice(0, 5)); // "Oct 23"
            const data = hist.map(d => d.mood_score);

            if (window.Chart) {
                this.chart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Mood',
                            data: data,
                            borderColor: '#8B5CF6',
                            tension: 0.4,
                            fill: true,
                            backgroundColor: 'rgba(139, 92, 246, 0.2)'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: { min: 1, max: 10 }
                        }
                    }
                });
            }
        } catch (e) { }
    }
};

// Bind range slider events dynamically
document.addEventListener("DOMContentLoaded", () => {
    const m = document.getElementById("journal-mood");
    const e = document.getElementById("journal-energy");
    if (m) m.addEventListener("input", () => window.journalHandler?.updateMoodDisplay());
    if (e) e.addEventListener("input", () => window.journalHandler?.updateMoodDisplay());
});
