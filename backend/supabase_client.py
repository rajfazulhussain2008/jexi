# supabase_client.py — Supabase client initialization and utilities

import os
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY

# Global Supabase client instances
_supabase_admin: Client = None
_supabase_client: Client = None

def get_supabase_admin() -> Client:
    """
    Get Supabase client with service role key (admin privileges).
    Use for backend operations that require elevated permissions.
    """
    global _supabase_admin
    
    if _supabase_admin is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment variables")
        
        _supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    
    return _supabase_admin

def get_supabase_client() -> Client:
    """
    Get Supabase client with anonymous key (limited permissions).
    Use for client-side operations or when user context is needed.
    """
    global _supabase_client
    
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
        
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    
    return _supabase_client

def is_supabase_configured() -> bool:
    """Check if Supabase is properly configured with required environment variables."""
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY and SUPABASE_ANON_KEY)

# Authentication helpers
async def sign_up_user(email: str, password: str, metadata: dict = None):
    """Register a new user with Supabase Auth."""
    supabase = get_supabase_client()
    return supabase.auth.sign_up({
        "email": email,
        "password": password,
        "options": {
            "data": metadata or {}
        }
    })

async def sign_in_user(email: str, password: str):
    """Sign in a user with Supabase Auth."""
    supabase = get_supabase_client()
    return supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })

async def sign_out_user(access_token: str):
    """Sign out a user."""
    supabase = get_supabase_client()
    supabase.auth.set_session(access_token, "")
    return supabase.auth.sign_out()

async def get_user_from_token(access_token: str):
    """Get user information from JWT token."""
    supabase = get_supabase_client()
    supabase.auth.set_session(access_token, "")
    return supabase.auth.get_user()

# Database helpers
def get_table(table_name: str):
    """Get a reference to a Supabase table."""
    supabase = get_supabase_admin()
    return supabase.table(table_name)

def execute_query(table_name: str, operation_type: str = "select", **kwargs):
    """
    Execute a database operation on a Supabase table.
    
    Args:
        table_name: Name of the table
        operation_type: Type of operation (select, insert, update, delete)
        **kwargs: Additional parameters for the operation
    """
    table = get_table(table_name)
    
    if operation_type == "select":
        return table.select(*kwargs.get("columns", "*")).execute()
    elif operation_type == "insert":
        return table.insert(kwargs.get("data", {})).execute()
    elif operation_type == "update":
        return table.update(kwargs.get("data", {})).eq("id", kwargs.get("id")).execute()
    elif operation_type == "delete":
        return table.delete().eq("id", kwargs.get("id")).execute()
    else:
        raise ValueError(f"Unsupported operation type: {operation_type}")
