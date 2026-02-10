import os
import streamlit as st
from supabase import create_client, Client

# --- SUPABASE CONNECTION ---
# Tries to get secrets from Streamlit (Cloud) or Environment (Local)
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase secrets are missing. Please check .streamlit/secrets.toml or Environment Variables.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def login_user(email, password):
    """
    Authenticates a user with Supabase Auth.
    Returns: (user_data_dict, None) on success, (None, error_message) on failure.
    """
    try:
        # 1. Auth with Supabase
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        user = res.user
        
        if user:
            # 2. Fetch User Profile (Role & Permissions) from 'users' table
            # We use .single() to get one dict instead of a list
            data_response = supabase.table("users").select("*").eq("id", user.id).execute()
            
            if data_response.data:
                profile = data_response.data[0]
                
                # Check if approved
                if not profile.get("is_approved", False):
                    return None, "Account is not approved yet. Please contact admin."
                
                # Merge Auth Data with Profile Data
                user_info = {
                    "id": user.id,
                    "email": user.email,
                    "role": profile.get("role", "employee"),
                    "allowed_modules": profile.get("allowed_modules", [])
                }
                return user_info, None
            else:
                return None, "User profile not found in database."
        else:
            return None, "Authentication failed."

    except Exception as e:
        return None, str(e)

def register_user(email, password, role="customer"):
    """
    Registers a new user in Supabase Auth AND creates a row in the 'users' table.
    Default role is 'customer'.
    Returns: (True, SuccessMsg) or (False, ErrorMsg)
    """
    try:
        # 1. Sign Up (Auth)
        res = supabase.auth.sign_up({"email": email, "password": password})
        user = res.user

        if user:
            # 2. Create Profile in 'users' table
            # Default: Not approved, basic permissions based on role
            
            # Default permissions for a customer
            default_modules = []
            if role == "customer":
                # Give access to Portal (9), Market(91), Export(92)
                default_modules = [9, 91, 92]
            
            payload = {
                "id": user.id,
                "email": email,
                "role": role,
                "is_approved": False, # Requires admin approval
                "allowed_modules": default_modules
            }
            
            supabase.table("users").insert(payload).execute()
            return True, "Registration successful! Please wait for admin approval."
        
        return False, "Registration failed (No user returned)."

    except Exception as e:
        return False, str(e)

def insert_record(table_name, payload):
    """
    Generic function to insert a record into any table.
    """
    try:
        supabase.table(table_name).insert(payload).execute()
        return True, None
    except Exception as e:
        return False, str(e)

def get_all_users():
    """
    Fetches all users for the Admin panel.
    """
    try:
        res = supabase.table("users").select("*").execute()
        return res.data
    except:
        return []

def update_user_permissions(user_id, is_approved, allowed_modules, role):
    """
    Updates a user's profile (Admin action).
    Now accepts 'role' as the 4th argument.
    """
    try:
        payload = {
            "is_approved": is_approved,
            "allowed_modules": allowed_modules,
            "role": role
        }
        supabase.table("users").update(payload).eq("id", user_id).execute()
        return True
    except Exception as e:
        print(f"Update error: {e}")
        return False
