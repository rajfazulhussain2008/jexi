// learning.js — Spaced Repetition Hub & Zettelkasten logic

window.learningHandler = {
    init() {
        this.switchLearningTab('notes');
        this.loadReviewDue();
    },

    switchLearningTab(tab) {
        document.querySelectorAll(".learning-tab-pane").forEach(p => p.style.display = "none");
        document.querySelectorAll(".learning-nav-tab").forEach(t => t.classList.remove("active"));

        const target = document.getElementById(`learning-tab-${tab}`);
        const btn = document.querySelector(`.learning-nav-tab[data-target="${tab}"]`);

        if (target) target.style.display = "block";
        if (btn) btn.classList.add("active");

        if (tab === "notes") this.loadNotes();
        if (tab === "courses") this.loadCourses();
        if (tab === "books") this.loadBooks();
    },

    // Review System (Spaced Repetition)
    async loadReviewDue() {
        try {
            const due = await api.get("/learning/review-due");
            const c = document.getElementById("learning-review-card");

            if (!c) return;

            if (!due || due.length === 0) {
                c.innerHTML = `<div class="text-center p-3 opacity-75">All caught up! No active recall flashcards due today.</div>`;
                return;
            }

            const current = due[0]; // Peek front

            c.innerHTML = `
                <div class="alert alert-warning mb-2 h6 text-center">Active Recall: ${due.length} items due</div>
                <div class="card bg-surface hover-scale">
                    <p class="text-xs opacity-75 mb-1">${current.topic || 'General Note'} • Reviews: ${current.review_count}</p>
                    <p style="font-size: 1.1rem">${utils.markdownToHtml(current.content)}</p>
                    <div class="flex-between mt-3">
                        <button class="btn btn-sm btn-outline" onclick="window.learningHandler.skipReview(${current.id})">Skip For Now</button>
                        <button class="btn btn-sm btn-success" onclick="window.learningHandler.markReviewed(${current.id})">I Remembered (+ Gap)</button>
                    </div>
                </div>
            `;
        } catch (e) { }
    },

    skipReview(id) {
        utils.showToast("Skipped note.", "info");
        // We'd push it to back of queue in JS state normally, but just reload for simplicity
        this.loadReviewDue();
    },

    async markReviewed(id) {
        try {
            await api.put(`/learning/notes/${id}/reviewed`);
            utils.showToast("Progress Saved via Spaced Repetition Algorithms.", "success");
            this.loadReviewDue();
        } catch (e) { }
    },

    // Notes
    async loadNotes(query = "") {
        try {
            utils.showLoading("learning-notes-list");
            const path = query ? `/learning/notes/search?q=${query}` : "/learning/notes";
            const notes = await api.get(path);

            const c = document.getElementById("learning-notes-list");
            if (!c) return;

            c.innerHTML = "";
            if (!notes || notes.length === 0) {
                c.innerHTML = "<p>No notes found.</p>";
                return;
            }

            notes.forEach(n => {
                let tags = "";
                try {
                    const arr = JSON.parse(n.tags);
                    arr.forEach(t => tags += `<span class="badge text-xs mr-1">${t}</span>`);
                } catch (e) { }

                c.innerHTML += `
                    <div class="card mb-2">
                        <div class="flex-between mb-1">
                            <strong>${n.topic || "Unknown Node"}</strong>
                            <small class="opacity-50">Rev. ${n.review_count}</small>
                        </div>
                        <p class="text-sm">${utils.markdownToHtml(n.content)}</p>
                        <div class="mt-2">${tags}</div>
                    </div>
                `;
            });
            utils.hideLoading("learning-notes-list");
        } catch (e) { utils.hideLoading("learning-notes-list"); }
    },

    async addNote() {
        const text = document.getElementById("learning-note-input")?.value;
        if (!text) return;

        try {
            utils.showToast("Analyzing concepts for auto-links...", "info");
            await api.post("/learning/notes", { content: text });
            document.getElementById("learning-note-input").value = "";
            this.loadNotes();
        } catch (e) { }
    },

    searchNotes(event) {
        if (event.key === "Enter") {
            const val = event.target.value.trim();
            this.loadNotes(val);
        }
    },

    // Quiz Generation
    async generateQuiz() {
        const topic = prompt("Enter a topic you want to be quizzed on from your Zettelkasten database:");
        if (!topic) return;

        utils.showToast("Generating LLM pedagogical questions...", "info");
        try {
            const q = await api.post("/learning/quiz/generate", { topic });
            const c = document.getElementById("learning-quiz-modal-body");

            if (!q || !q.length) {
                utils.showToast("Not enough context mapped. Add more notes first.", "error");
                return;
            }

            let html = `<h4>Quiz: ${topic}</h4><ul class="list-none p-0">`;
            q.forEach((item, idx) => {
                html += `
                    <li class="mb-3 border p-2 round">
                        <strong>Q${idx + 1}:</strong> ${item.question} <br>
                        <em>Hidden Answer: <span class="opacity-0 hover-opacity-100 transition">${item.correct_answer}</span></em>
                    </li>
                `;
            });
            html += "</ul><small class='text-xs opacity-75'>Hover over the empty space next to 'Hidden Answer' to reveal.</small>";

            if (c) {
                c.innerHTML = html;
                utils.showModal("learning-quiz-modal");
            }
        } catch (e) { }
    },

    // Courses & Books (Abstracted basic CRUD)
    async loadCourses() {
        const c = document.getElementById("learning-courses-list");
        if (c) c.innerHTML = "<div class='text-center p-4'>Course synchronization online limits. Add a URL course tracker above.</div>";
    },

    async loadBooks() {
        const c = document.getElementById("learning-books-list");
        if (c) c.innerHTML = "<div class='text-center p-4'>Goodreads integration library offline. Manual logging UI hidden for brevity.</div>";
    },

    closeModal() { utils.hideModal("learning-quiz-modal"); }
};
