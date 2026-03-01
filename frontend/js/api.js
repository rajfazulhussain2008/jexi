// api.js — API Communication Layer

class API {
    constructor() {
        // Automatically switch between relative path (website) 
        // and absolute path (mobile app)
        this.baseUrl = window.JEXI_CONFIG?.API_URL || "/api/v1";
        this.tokenKey = "jexi_token";
        this.useSupabase = window.JEXI_CONFIG?.USE_SUPABASE || false;
    }

    getToken() {
        let token = localStorage.getItem(this.tokenKey);
        // Try getting from Android Bridge if not in localStorage
        if (!token && window.JexiBridge && window.JexiBridge.getAuthToken) {
            try {
                token = window.JexiBridge.getAuthToken();
                if (token) localStorage.setItem(this.tokenKey, token);
            } catch (e) {
                console.error("Bridge getToken failed:", e);
            }
        }
        return token;
    }

    isLoggedIn() {
        if (this.useSupabase && window.supabaseClient) {
            return window.supabaseClient.isLoggedIn();
        }
        return !!this.getToken();
    }

    isAdmin() {
        return localStorage.getItem("jexi_is_admin") === "true";
    }

    logout() {
        if (this.useSupabase && window.supabaseClient) {
            window.supabaseClient.signOut();
        }
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem("jexi_is_admin");

        // Notify Android Native Bridge
        if (window.JexiBridge && window.JexiBridge.clearAuthToken) {
            try {
                window.JexiBridge.clearAuthToken();
            } catch (e) { }
        }

        // Dispatch event or direct call to app structure
        if (window.app) window.app.showLoginScreen();
    }

    async request(method, path, body = null) {
        // 1. Android Native Bridge Interception
        if (window.JexiBridge && method !== "GET") {
            try {
                // If we are in Android and making a write request, 
                // we tell the native side to log this for later sync if offline.
                window.JexiBridge.logOfflineAction(method, path, JSON.stringify(body));
            } catch (e) {
                console.error("Android Bridge Error:", e);
            }
        }

        const headers = {
            "Content-Type": "application/json"
        };

        const token = this.getToken();
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        const options = {
            method,
            headers
        };

        if (body && method !== "GET") {
            options.body = JSON.stringify(body);
        }

        try {
            // Check internet status
            if (!navigator.onLine) {
                throw new Error("Offline: No internet connection.");
            }

            const response = await fetch(`${this.baseUrl}${path}`, options);

            let data = null;
            const text = await response.text();
            if (text) {
                try {
                    data = JSON.parse(text);
                } catch (e) {
                    data = text;
                }
            }

            if (response.status === 401) {
                const msg = (data && data.detail) ? data.detail : "Unauthorized. Please log in again.";
                throw new Error(msg);
            }

            if (!response.ok) {
                const errorMsg = data && data.detail ? data.detail : `Error ${response.status}: ${response.statusText}`;
                throw new Error(errorMsg);
            }

            // Cache successful GET requests for offline viewing
            if (method === "GET") {
                localStorage.setItem(`cache${path}`, JSON.stringify(data));
            }

            return data;
        } catch (error) {
            // FALLBACK: If offline or network error, check cache for GET requests
            if (method === "GET") {
                const cachedData = localStorage.getItem(`cache${path}`);
                if (cachedData) {
                    console.warn(`Serving cached data for ${path} due to error:`, error.message);
                    return JSON.parse(cachedData);
                }
            }

            // Don't show toast for 401 on non-auth routes
            if (!error.message.includes("Unauthorized") && !error.message.includes("Offline")) {
                utils.showToast(error.message, "error");
            }
            throw error;
        }
    }

    // New helper for Android to sync all local changes to the cloud
    async syncPendingData() {
        if (!navigator.onLine) return;
        console.log("Syncing pending data to cloud...");
        // This is called by the Android bridge when network returns
    }

    async get(path) {
        return this.request("GET", path);
    }

    async post(path, body) {
        return this.request("POST", path, body);
    }

    async put(path, body) {
        return this.request("PUT", path, body);
    }

    async del(path) {
        return this.request("DELETE", path);
    }

    async upload(path, file) {
        const formData = new FormData();
        formData.append("file", file);

        const headers = {};
        const token = this.getToken();
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(`${this.baseUrl}${path}`, {
                method: "POST",
                headers,
                body: formData
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || "Upload failed");
            }

            return await response.json();
        } catch (error) {
            console.error("Upload error:", error);
            utils.showToast(error.message, "error");
            throw error;
        }
    }

    async login(username, password) {
        try {
            if (this.useSupabase && window.supabaseClient) {
                // Use Supabase authentication
                const data = await window.supabaseClient.signIn(username, password);

                if (data.user && data.session) {
                    localStorage.setItem("jexi_is_admin", data.user.user_metadata?.is_admin || false);
                    utils.showToast("Login successful", "success");
                    return true;
                } else {
                    throw new Error("Invalid response from Supabase");
                }
            } else {
                // Use existing API authentication
                const data = await this.post("/auth/login", { username, password });

                if (data && data.status === "success" && data.data.token) {
                    const token = data.data.token;
                    localStorage.setItem(this.tokenKey, token);
                    localStorage.setItem("jexi_is_admin", data.data.is_admin || false);

                    // Sync to Android Native Bridge
                    if (window.JexiBridge && window.JexiBridge.saveAuthToken) {
                        window.JexiBridge.saveAuthToken(token);
                    }

                    utils.showToast("Login successful", "success");
                    return true;
                } else if (data && data.access_token) {
                    const token = data.access_token;
                    localStorage.setItem(this.tokenKey, token);
                    localStorage.setItem("jexi_is_admin", data.is_admin || false);

                    // Sync to Android Native Bridge
                    if (window.JexiBridge && window.JexiBridge.saveAuthToken) {
                        window.JexiBridge.saveAuthToken(token);
                    }

                    utils.showToast("Login successful", "success");
                    return true;
                } else {
                    throw new Error("Invalid response format from server");
                }
            }
        } catch (error) {
            throw error;
        }
    }

    async setup(username, password) {
        try {
            if (this.useSupabase && window.supabaseClient) {
                // Use Supabase authentication
                const data = await window.supabaseClient.signUp(username, password, { is_admin: true });

                if (data.user && data.session) {
                    localStorage.setItem("jexi_is_admin", true);
                    utils.showToast("Account created successfully", "success");
                    return true;
                } else {
                    throw new Error("Invalid response from Supabase");
                }
            } else {
                // Use existing API authentication
                const response = await this.post("/auth/setup", { username, password });
                // Be lenient: handle different response formats
                const token = response?.data?.token || response?.token || response?.access_token;
                const isAdmin = response?.data?.is_admin ?? response?.is_admin ?? false;
                if (token) {
                    localStorage.setItem(this.tokenKey, token);
                    localStorage.setItem("jexi_is_admin", isAdmin);

                    // Sync to Android Native Bridge
                    if (window.JexiBridge && window.JexiBridge.saveAuthToken) {
                        window.JexiBridge.saveAuthToken(token);
                    }
                }
                utils.showToast("Account created successfully", "success");
                return true;
            }
        } catch (error) {
            throw error;
        }
    }
}

const api = new API();
