// chat.js — AI Chat Interactions

window.chatHandler = {
    sessionId: null,
    voiceEnabled: false,

    initChat() {
        this.sessionId = utils.getFromLocal("jexi_chat_session") || utils.generateId();
        utils.saveToLocal("jexi_chat_session", this.sessionId);
        this.voiceEnabled = utils.getFromLocal("jexi_voice_enabled") === true;

        const input = document.getElementById("chatTextarea");
        if (input) {
            input.removeEventListener("keydown", this.handleKeyDown); // Prevent duplicate events
            input.addEventListener("keydown", (e) => this.handleKeyDown(e));
            input.addEventListener("input", (e) => {
                this.autoResize(e);
                this.saveDraft(e.target.value);
            });
            this.loadDraft();
        }

        const sendBtn = document.getElementById("chatSendBtn");
        if (sendBtn) {
            sendBtn.onclick = () => this.sendMessage();
        }

        const newBtn = document.getElementById("newChatBtn");
        if (newBtn) {
            newBtn.onclick = () => this.newChat();
        }

        // Bind suggested action buttons
        const suggestedBtns = document.querySelectorAll(".btn-suggested");
        suggestedBtns.forEach(btn => {
            btn.onclick = () => this.sendQuick(btn.textContent);
        });
    },

    handleKeyDown(event) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            this.sendMessage();
        }
    },

    autoResize(e) {
        const target = e.target;
        target.style.height = "auto";
        target.style.height = (target.scrollHeight) + "px";
    },

    async sendMessage() {
        const input = document.getElementById("chatTextarea");
        if (!input) return;

        const text = input.value.trim();
        if (!text) return;

        // Add user message to UI
        this.addMessage("user", text);
        input.value = "";
        input.style.height = "auto";

        this.showTyping();

        // Get optional provider
        const providerSelect = document.getElementById("globalProviderSelect");
        const providerVal = providerSelect ? providerSelect.value : "";

        try {
            const result = await api.post("/ai/chat", {
                message: text,
                session_id: this.sessionId,
                provider: providerVal || null
            });

            this.removeTyping();

            if (result && result.status === "success" && result.data) {
                const answer = result.data.text || "No response generated.";
                const timeStr = `${result.data.response_time || 0}s`;
                this.addMessage("assistant", answer, result.data.provider, result.data.model, timeStr);

                if (this.voiceEnabled) {
                    this.speak(answer);
                }
            } else {
                this.addMessage("assistant", "I received an unexpected response structure from the server.");
            }
        } catch (err) {
            console.error("Chat error:", err);
            this.removeTyping();
            this.addMessage("assistant", "I'm sorry, an error occurred while processing your request.");
        }
    },

    sendQuick(text) {
        const input = document.getElementById("chatTextarea");
        if (input) {
            input.value = text;
            this.sendMessage();
        }
    },

    addMessage(role, text, provider = null, model = null, time = null) {
        const container = document.getElementById("chatMessagesBox");
        if (!container) return;

        // Hide welcome if it's visible
        const welcome = container.querySelector(".chat-welcome");
        if (welcome) welcome.style.display = "none";

        const wrapper = document.createElement("div");
        wrapper.className = `message-wrapper msg-${role === 'user' ? 'user' : 'ai'}`;

        if (role === 'assistant') {
            const avatar = document.createElement("div");
            avatar.className = "msg-avatar";
            avatar.innerHTML = '<i class="fas fa-robot"></i>';
            wrapper.appendChild(avatar);
        }

        const content = document.createElement("div");
        content.className = "msg-content";
        content.innerHTML = utils.markdownToHtml(text);

        if (role === "assistant" && provider) {
            const meta = document.createElement("div");
            meta.className = "chat-meta";
            meta.style.fontSize = "0.75rem";
            meta.style.opacity = "0.7";
            meta.style.marginTop = "5px";
            meta.textContent = `${provider} (${model || 'default'}) ⚡ ${time}`;
            content.appendChild(meta);
        }

        wrapper.appendChild(content);
        container.appendChild(wrapper);

        // Scroll
        container.scrollTop = container.scrollHeight;
    },

    showTyping() {
        const container = document.getElementById("chatMessagesBox");
        if (!container) return;

        const wrapper = document.createElement("div");
        wrapper.id = "chat-typing";
        wrapper.className = "message-wrapper msg-ai";
        wrapper.innerHTML = `
            <div class="msg-avatar"><i class="fas fa-robot"></i></div>
            <div class="msg-content typing-dots"><span>.</span><span>.</span><span>.</span></div>
        `;
        container.appendChild(wrapper);
        container.scrollTop = container.scrollHeight;
    },

    removeTyping() {
        const typing = document.getElementById("chat-typing");
        if (typing) typing.remove();
    },

    newChat() {
        this.sessionId = utils.generateId();
        utils.saveToLocal("jexi_chat_session", this.sessionId);

        const container = document.getElementById("chatMessagesBox");
        if (container) {
            container.innerHTML = `
                <div class="chat-welcome" style="display: block;">
                    <i class="fas fa-robot welcome-icon"></i>
                    <h3>How can I help you today?</h3>
                    <div class="chat-suggested-actions">
                        <button class="btn-suggested">Organize my tasks</button>
                        <button class="btn-suggested">Analyze my budget</button>
                        <button class="btn-suggested">Help me debug code</button>
                        <button class="btn-suggested">Give me a motivational quote</button>
                    </div>
                </div>
             `;
            // Re-bind buttons since we just innerHTML'd them
            this.initChat();
        }
    },

    speak(text) {
        if (!('speechSynthesis' in window)) return;
        window.speechSynthesis.cancel();
        const cleanText = text.replace(/[*_#`~]/g, "").trim();
        const utterance = new SpeechSynthesisUtterance(cleanText);
        window.speechSynthesis.speak(utterance);
    },

    saveDraft(content) {
        utils.saveToDB("cache", "current_chat_draft", content);
    },

    async loadDraft() {
        const draft = await utils.getFromDB("cache", "current_chat_draft");
        const input = document.getElementById("chatTextarea");
        if (draft && input) {
            input.value = draft;
            this.autoResize({ target: input });
        }
    }
};
