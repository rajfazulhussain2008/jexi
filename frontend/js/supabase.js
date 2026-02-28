// supabase.js — Supabase client initialization and utilities for frontend

class SupabaseClient {
    constructor() {
        this.supabase = null;
        this.user = null;
        this.initialized = false;
    }

    async initialize() {
        if (this.initialized) return;

        // Configuration should be loaded from environment or config
        // For now, we'll expect these to be available globally
        const supabaseUrl = window.JEXI_CONFIG?.SUPABASE_URL || process.env.SUPABASE_URL;
        const supabaseAnonKey = window.JEXI_CONFIG?.SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY;

        if (!supabaseUrl || !supabaseAnonKey) {
            console.warn('Supabase configuration missing. Please set SUPABASE_URL and SUPABASE_ANON_KEY');
            return;
        }

        this.supabase = window.supabase.createClient(supabaseUrl, supabaseAnonKey);
        
        // Set up auth state listener
        this.supabase.auth.onAuthStateChange((event, session) => {
            this.user = session?.user || null;
            
            // Store session in localStorage for persistence
            if (session) {
                localStorage.setItem('supabase_session', JSON.stringify(session));
                localStorage.setItem('jexi_token', session.access_token);
            } else {
                localStorage.removeItem('supabase_session');
                localStorage.removeItem('jexi_token');
            }

            // Dispatch custom event for other parts of the app
            window.dispatchEvent(new CustomEvent('supabaseAuthChange', {
                detail: { event, session, user: this.user }
            }));
        });

        // Restore session if exists
        const savedSession = localStorage.getItem('supabase_session');
        if (savedSession) {
            try {
                const session = JSON.parse(savedSession);
                await this.supabase.auth.setSession(session.access_token, session.refresh_token);
            } catch (error) {
                console.error('Failed to restore Supabase session:', error);
                localStorage.removeItem('supabase_session');
            }
        }

        this.initialized = true;
    }

    async signUp(email, password, metadata = {}) {
        await this.initialize();
        const { data, error } = await this.supabase.auth.signUp({
            email,
            password,
            options: {
                data: metadata
            }
        });
        
        if (error) throw error;
        return data;
    }

    async signIn(email, password) {
        await this.initialize();
        const { data, error } = await this.supabase.auth.signInWithPassword({
            email,
            password
        });
        
        if (error) throw error;
        return data;
    }

    async signOut() {
        await this.initialize();
        const { error } = await this.supabase.auth.signOut();
        if (error) throw error;
    }

    async resetPassword(email) {
        await this.initialize();
        const { data, error } = await this.supabase.auth.resetPasswordForEmail(email);
        if (error) throw error;
        return data;
    }

    async updatePassword(newPassword) {
        await this.initialize();
        const { data, error } = await this.supabase.auth.updateUser({
            password: newPassword
        });
        if (error) throw error;
        return data;
    }

    async updateUser(metadata) {
        await this.initialize();
        const { data, error } = await this.supabase.auth.updateUser({
            data: metadata
        });
        if (error) throw error;
        return data;
    }

    getCurrentUser() {
        return this.user;
    }

    isLoggedIn() {
        return !!this.user;
    }

    // Database operations
    async from(table) {
        await this.initialize();
        return this.supabase.from(table);
    }

    // Storage operations
    async storage() {
        await this.initialize();
        return this.supabase.storage;
    }

    // Real-time subscriptions
    async channel(name) {
        await this.initialize();
        return this.supabase.channel(name);
    }
}

// Create global instance
window.supabaseClient = new SupabaseClient();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.supabaseClient.initialize();
});
