# test_supabase.py - Test Supabase connection and basic functionality

import os
import sys
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

def test_supabase_connection():
    """Test Supabase connection and configuration"""
    print("🧪 Testing Supabase Integration...")
    
    # Check environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
    
    print(f"✅ SUPABASE_URL: {'✓ Set' if supabase_url else '✗ Missing'}")
    print(f"✅ SUPABASE_SERVICE_ROLE_KEY: {'✓ Set' if supabase_service_key else '✗ Missing'}")
    print(f"✅ SUPABASE_ANON_KEY: {'✓ Set' if supabase_anon_key else '✗ Missing'}")
    
    if not all([supabase_url, supabase_service_key, supabase_anon_key]):
        print("❌ Some environment variables are missing!")
        return False
    
    try:
        # Test Supabase client import and initialization
        from supabase_client import get_supabase_admin, is_supabase_configured
        
        print(f"✅ Supabase module imported successfully")
        print(f"✅ Supabase configured: {is_supabase_configured()}")
        
        if is_supabase_configured():
            # Test admin client
            admin_client = get_supabase_admin()
            print(f"✅ Admin client created successfully")
            
            # Test basic operation - try to get auth users
            try:
                # This will test if the connection works
                response = admin_client.auth.get_user('test')
                print("✅ Supabase connection test passed")
            except Exception as e:
                if "Invalid JWT" in str(e):
                    print("✅ Supabase connection working (expected JWT error for test)")
                else:
                    print(f"⚠️  Unexpected error: {e}")
            
            return True
        else:
            print("❌ Supabase not properly configured")
            return False
            
    except ImportError as e:
        print(f"❌ Failed to import Supabase client: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing Supabase: {e}")
        return False

def test_database_connection():
    """Test database connection and basic operations"""
    print("\n🗄️  Testing Database Connection...")
    
    try:
        from supabase_client import get_supabase_admin
        
        client = get_supabase_admin()
        
        # Test if we can access the profiles table
        try:
            response = client.table('profiles').select('count').execute()
            print("✅ Database connection successful")
            return True
        except Exception as e:
            if "relation \"public.profiles\" does not exist" in str(e):
                print("⚠️  Profiles table not created yet. Run the SQL scripts in Supabase dashboard.")
            else:
                print(f"❌ Database error: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("JEXI - Supabase Integration Test")
    print("=" * 50)
    
    # Test connection
    connection_ok = test_supabase_connection()
    
    # Test database
    if connection_ok:
        database_ok = test_database_connection()
    else:
        database_ok = False
    
    print("\n" + "=" * 50)
    if connection_ok and database_ok:
        print("🎉 All tests passed! Supabase integration is ready.")
        print("\nNext steps:")
        print("1. Start your backend server")
        print("2. Open the frontend in your browser")
        print("3. Try signing up/logging in with Supabase")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    print("=" * 50)
