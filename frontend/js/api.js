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
        return localStorage.getItem(this.tokenKey);
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
        // Dispatch event or direct call to app structure
        if (window.app) window.app.showLoginScreen();
    }

    async request(method, path, body = null) {
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
            const response = await fetch(`${this.baseUrl}${path}`, options);

            if (response.status === 401) {
                // Only auto-logout if the token itself is invalid (not for missing endpoints)
                if (path.includes("/auth/me") || path.includes("/auth/login")) {
                    this.logout();
                }
                throw new Error("Unauthorized. Please log in again.");
            }

            let data = null;
            const text = await response.text();
            if (text) {
                try {
                    data = JSON.parse(text);
                } catch (e) {
                    data = text;
                }
            }

            if (!response.ok) {
                const errorMsg = data && data.detail ? data.detail : `Error ${response.status}: ${response.statusText}`;
                throw new Error(errorMsg);
            }

            return data;
        } catch (error) {
            // Don't show toast for 401 on non-auth routes (background API calls)
            if (!error.message.includes("Unauthorized")) {
                utils.showToast(error.message, "error");
            }
            throw error;
        }
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
                    localStorage.setItem(this.tokenKey, data.data.token);
                    localStorage.setItem("jexi_is_admin", data.data.is_admin || false);
                    utils.showToast("Login successful", "success");
                    return true;
                } else if (data && data.access_token) {
                    localStorage.setItem(this.tokenKey, data.access_token);
                    localStorage.setItem("jexi_is_admin", data.is_admin || false);
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
