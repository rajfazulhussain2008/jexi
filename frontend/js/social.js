// social.js — Friends & Community Interactions

window.socialHandler = {
    friends: [],
    activeFriendId: null,

    async loadFriends() {
        try {
            const resp = await api.get("/social/friends");
            // Handle response format: {status, data: [...]} or plain array
            if (resp && resp.status === "success" && Array.isArray(resp.data)) {
                this.friends = resp.data;
            } else if (Array.isArray(resp)) {
                this.friends = resp;
            } else {
                this.friends = [];
            }
            this.renderFriendsSidebar();
            this.setupEventListeners();
            this.loadCommunity();
        } catch (e) {
            console.error("Failed to load friends", e);
            this.friends = [];
            this.renderFriendsSidebar();
        }
    },

    setupEventListeners() {
        const input = document.getElementById("friendChatInput");
        if (input) {
            input.onkeydown = (e) => {
                if (e.key === "Enter") this.sendFriendMessage();
            };
        }

        const attachBtn = document.getElementById("friendAttachBtn");
        const fileInput = document.getElementById("friendChatFile");
        if (attachBtn && fileInput) {
            attachBtn.onclick = () => fileInput.click();
            fileInput.onchange = (e) => this.handleFileSelect(e);
        }

        const sendBtn = document.getElementById("friendSendBtn");
        if (sendBtn) {
            sendBtn.onclick = () => this.sendFriendMessage();
        }

        const searchInput = document.getElementById("friendSearchInput");
        if (searchInput) {
            searchInput.oninput = (e) => this.filterFriends(e.target.value);
        }

        const addFriendBtn = document.getElementById("addFriendBtn");
        if (addFriendBtn) {
            addFriendBtn.onclick = () => {
                if (api.isAdmin()) {
                    if (window.app) window.app.switchView("adminView");
                } else {
                    utils.showToast("Ask Raj Mohamed H (Admin) to add you as a friend!", "info");
                }
            };
        }
    },

    renderFriendsSidebar() {
        const list = document.getElementById("friendsSidebarList");
        if (!list) return;

        if (!this.friends || this.friends.length === 0) {
            list.innerHTML = "<p class='text-muted p-3 text-center'>No friends found.</p>";
            return;
        }

        list.innerHTML = "";
        this.friends.forEach(f => {
            const item = document.createElement("div");
            item.className = `friend-item ${f.id === this.activeFriendId ? 'active' : ''}`;
            item.onclick = () => this.switchFriend(f.id);

            item.innerHTML = `
                <img src="${f.avatar}" alt="${f.name}" class="avatar-sm">
                <div class="friend-info">
                    <div class="friend-name">${f.name} <span class="status-${f.status}"></span></div>
                    <div class="friend-last-msg">${f.lastMsg}</div>
                </div>
                <div class="friend-meta">${f.time}</div>
            `;
            list.appendChild(item);
        });
    },

    chatPollInterval: null,

    async switchFriend(id) {
        this.activeFriendId = id;
        const friend = this.friends.find(f => f.id === id);
        if (!friend) return;

        // Update Header
        document.getElementById("activeFriendName").textContent = friend.name;
        document.getElementById("activeFriendAvatar").src = friend.friend_avatar || friend.avatar;

        this.renderFriendsSidebar();

        if (this.chatPollInterval) {
            clearInterval(this.chatPollInterval);
        }

        await this.loadChatMessages();

        // Poll for new messages every 3 seconds
        this.chatPollInterval = setInterval(() => this.loadChatMessages(true), 3000);
    },

    async loadChatMessages(isPolling = false) {
        if (!this.activeFriendId) return;

        try {
            const messages = await api.get(`/social/messages/${this.activeFriendId}`);
            const msgBox = document.getElementById("friendsMessagesBox");
            if (!msgBox) return;

            // Simple check if user is scrolled to bottom before updating
            const isScrolledToBottom = msgBox.scrollHeight - msgBox.clientHeight <= msgBox.scrollTop + 50;

            if (messages.length === 0) {
                if (!isPolling) {
                    msgBox.innerHTML = `
                        <div class="empty-state py-5">
                            <p class="text-muted">Chat history will appear here.</p>
                        </div>
                    `;
                }
                return;
            }

            // Rebuild HTML (in a robust app this would diff or append)
            let html = "";
            messages.forEach(msg => {
                const isMe = msg.sender_id !== this.activeFriendId;
                const timeStr = new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                let attachmentHtml = "";
                if (msg.attachment_url) {
                    if (msg.attachment_url.match(/\.(jpeg|jpg|gif|png|webp|svg)$/i)) {
                        attachmentHtml = `<div class="msg-attachment"><img src="${msg.attachment_url}" class="chat-img" onclick="window.open('${msg.attachment_url}', '_blank')"></div>`;
                    } else {
                        attachmentHtml = `<div class="msg-attachment"><a href="${msg.attachment_url}" target="_blank" class="chat-file-link"><i class="fas fa-file"></i> View Attachment</a></div>`;
                    }
                }

                html += `
                    <div class="message-wrapper ${isMe ? 'msg-me' : 'msg-friend'}">
                        <div class="msg-content">
                            ${attachmentHtml}
                            ${msg.content ? `<span>${msg.content}</span>` : ''}
                        </div>
                        <div class="msg-time">${timeStr}</div>
                    </div>
                `;
            });

            msgBox.innerHTML = html;

            // Scroll down automatically if we just loaded or were already at bottom
            if (!isPolling || isScrolledToBottom) {
                msgBox.scrollTop = msgBox.scrollHeight;
            }
        } catch (e) {
            console.error("Failed to load messages", e);
        }
    },

    filterFriends(query) {
        const items = document.querySelectorAll(".friend-item");
        items.forEach(item => {
            const name = item.querySelector(".friend-name").textContent.toLowerCase();
            if (name.includes(query.toLowerCase())) {
                item.style.display = "flex";
            } else {
                item.style.display = "none";
            }
        });
    },

    async handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        // Show a temporary indicator
        utils.showToast("Uploading attachment...", "info");

        try {
            const result = await api.upload("/social/upload", file);
            if (result && result.url) {
                this.sendFriendMessage(result.url);
            }
        } catch (e) {
            console.error("Upload failed", e);
        } finally {
            event.target.value = ""; // Clear file input
        }
    },

    async sendFriendMessage(attachmentUrl = null) {
        if (!this.activeFriendId) return;

        const input = document.getElementById("friendChatInput");
        const text = input ? input.value.trim() : "";

        if (!text && !attachmentUrl) return;

        if (input) input.value = ""; // clear instantly for good UX

        try {
            await api.post(`/social/messages/${this.activeFriendId}`, {
                content: text,
                attachment_url: attachmentUrl
            });
            await this.loadChatMessages(); // instantly reload chat
        } catch (e) {
            utils.showToast("Failed to send message", "error");
        }
    },

    // Stop polling when leaving the view
    cleanup() {
        if (this.chatPollInterval) {
            clearInterval(this.chatPollInterval);
            this.chatPollInterval = null;
        }
    },

    loadCommunity() {
        this.renderActivityFeed();
        this.renderLeaderboard();
    },

    async renderActivityFeed() {
        const feedList = document.querySelector("#communityView .feed-list");
        if (!feedList) return;

        try {
            // Fetch from backend
            const activities = await api.get("/social/activity");

            feedList.innerHTML = "";
            activities.forEach(item => {
                const bg = item.type === 'goal' ? 'bg-blue' : (item.type === 'streak' ? 'bg-purple' : 'bg-green');
                const div = document.createElement("div");
                div.className = "feed-item";
                div.innerHTML = `
                    <div class="feed-avatar text-white ${bg}"><i class="fas fa-user"></i></div>
                    <div class="feed-content">
                        <p><strong>${item.user}</strong> ${item.action}</p>
                        <span class="fs-sm text-muted">${item.time}</span>
                    </div>
                    <div class="feed-action"><i class="far fa-heart"></i></div>
                `;
                feedList.appendChild(div);
            });
        } catch (e) {
            console.error("Feed error", e);
        }
    },

    async renderLeaderboard() {
        const board = document.querySelector("#communityView .leaderboard-list");
        if (!board) return;

        try {
            const data = await api.get("/social/leaderboard");

            board.innerHTML = "";
            data.forEach(p => {
                const item = document.createElement("div");
                item.className = `leaderboard-item ${p.is_me ? 'me' : ''}`;
                item.innerHTML = `
                    <div class="lb-rank">${p.rank}</div>
                    <div class="lb-name">${p.name}</div>
                    <div class="lb-score">${p.score}</div>
                `;
                board.appendChild(item);
            });
        } catch (e) {
            console.error("Leaderboard error", e);
        }
    }
};
