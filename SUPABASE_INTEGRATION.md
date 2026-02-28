# Supabase Integration Guide for JEXI

## Overview
This guide outlines the Supabase integration that has been added to your JEXI web application. The integration provides authentication, database, and real-time capabilities.

## What's Been Added

### Backend Changes
1. **Supabase Python Client** - Added to `requirements.txt`
2. **Configuration** - Added Supabase environment variables to `config.py`
3. **Client Module** - Created `supabase_client.py` with:
   - Admin and client client initialization
   - Authentication helpers (sign up, sign in, sign out)
   - Database query helpers
   - Configuration validation

### Frontend Changes
1. **Supabase JS Client** - Added CDN link to `index.html`
2. **Client Wrapper** - Created `js/supabase.js` with:
   - Supabase client initialization
   - Authentication methods
   - Session management
   - Database and storage helpers
3. **API Integration** - Updated `js/api.js` to support both existing auth and Supabase auth

## Setup Instructions

### 1. Create a Supabase Project
1. Go to [supabase.com](https://supabase.com)
2. Create a new project
3. Note your project URL and anon key

### 2. Configure Environment Variables

#### Backend (.env)
```env
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key
```

#### Frontend Configuration
Add to your HTML or JavaScript config:
```javascript
window.JEXI_CONFIG = {
    USE_SUPABASE: true,
    SUPABASE_URL: "https://your-project-id.supabase.co",
    SUPABASE_ANON_KEY: "your-anon-key",
    API_URL: "/api/v1"  // Keep existing API for non-auth operations
};
```

### 3. Database Setup

#### Create Tables
Run these SQL commands in your Supabase SQL editor:

```sql
-- Users table (extends auth.users)
CREATE TABLE public.profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    username TEXT UNIQUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS (Row Level Security)
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Users can view own profile" ON public.profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Admins can view all profiles" ON public.profiles
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.profiles 
            WHERE id = auth.uid() AND is_admin = TRUE
        )
    );

-- Function to automatically create profile on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, username)
    VALUES (new.id, new.email);
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create profile on signup
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

#### Additional Tables (based on your existing models)
Create tables for your existing data models:
- tasks
- goals  
- habits
- journal_entries
- health_logs
- finance_records
- projects
- etc.

### 4. Migration Strategy

#### Option 1: Gradual Migration
1. Keep existing SQLite database for current functionality
2. Use Supabase only for authentication initially
3. Gradually migrate modules to use Supabase tables
4. Update API endpoints to use Supabase client

#### Option 2: Full Migration
1. Export existing data from SQLite
2. Create matching tables in Supabase
3. Import data to Supabase
4. Update all API endpoints to use Supabase
5. Remove SQLite dependency

### 5. Testing the Integration

#### Frontend Testing
```javascript
// Test Supabase connection
console.log('Supabase client:', window.supabaseClient);

// Test authentication
try {
    await window.supabaseClient.signIn('test@example.com', 'password');
    console.log('Auth successful');
} catch (error) {
    console.error('Auth failed:', error);
}
```

#### Backend Testing
```python
# Test Supabase connection
from supabase_client import get_supabase_admin, is_supabase_configured

print('Supabase configured:', is_supabase_configured())
if is_supabase_configured():
    client = get_supabase_admin()
    print('Supabase client created successfully')
```

## Usage Examples

### Authentication
```javascript
// Sign up
await window.supabaseClient.signUp('user@example.com', 'password', { username: 'john' });

// Sign in  
await window.supabaseClient.signIn('user@example.com', 'password');

// Sign out
await window.supabaseClient.signOut();

// Get current user
const user = window.supabaseClient.getCurrentUser();
```

### Database Operations
```javascript
// Insert data
const { data, error } = await window.supabaseClient
    .from('tasks')
    .insert([{ title: 'New task', completed: false }]);

// Query data
const { data, error } = await window.supabaseClient
    .from('tasks')
    .select('*')
    .eq('completed', false);

// Update data
const { data, error } = await window.supabaseClient
    .from('tasks')
    .update({ completed: true })
    .eq('id', taskId);
```

## Benefits of Supabase Integration

1. **Real-time Capabilities** - Automatic data synchronization
2. **Authentication** - Secure user management out of the box
3. **Row Level Security** - Fine-grained access control
4. **Scalability** - PostgreSQL backend with automatic scaling
5. **API Generation** - Automatic REST and GraphQL APIs
6. **Storage** - File storage for user uploads
7. **Edge Functions** - Serverless functions for custom logic

## Next Steps

1. Set up your Supabase project and configure environment variables
2. Create the necessary database tables
3. Test authentication flow
4. Gradually migrate your data models to Supabase
5. Implement real-time features where beneficial
6. Set up proper Row Level Security policies

## Troubleshooting

### Common Issues
- **CORS errors**: Ensure your frontend URL is added to Supabase CORS settings
- **Auth errors**: Check that your keys are correctly configured
- **RLS errors**: Verify Row Level Security policies are properly set up
- **Connection issues**: Ensure Supabase URL is correct and accessible

### Debug Mode
Enable debug logging:
```javascript
// In browser console
localStorage.setItem('supabase.debug', 'true');
```

## Support

- Supabase Documentation: https://supabase.com/docs
- Supabase Discord: https://discord.supabase.com
- This integration guide and code comments
