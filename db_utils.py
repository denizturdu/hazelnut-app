import os
import streamlit as st
from supabase import create_client, Client

# --- SUPABASE CONNECTION ---
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase secrets are missing.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def login_user(email, password):
    """
    Authenticates a user. 
    """
    try:
        # 1. Auth with Supabase
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        user = res.user
        
        if user:
            # 2. Fetch Profile from 'app_users'
            response = supabase.table("app_users").select("*").eq("id", user.id).execute()
            
            if response.data and len(response.data) > 0:
                profile = response.data[0]
                
                if not profile.get("is_approved", False):
                    return None, "Account pending approval."
                
                return {
                    "id": user.id,
                    "email": user.email,
                    "role": profile.get("role", "employee"),
                    "allowed_modules": profile.get("allowed_modules", [])
                }, None
            else:
                return None, "Profile missing in 'app_users' table. Contact Admin."
        else:
            return None, "Invalid credentials."

    except Exception as e:
        return None, f"Login Error: {str(e)}"

def register_user(email, password, role="customer"):
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        user = res.user

        if user:
            # Default permissions
            default_modules = [9, 91, 92] if role == "customer" else []
            
            payload = {
                "id": user.id,
                "email": email,
                "role": role,
                "is_approved": False,
                "allowed_modules": default_modules
            }
            # Insert into 'app_users'
            supabase.table("app_users").insert(payload).execute()
            return True, "Registration successful! Wait for approval."
        
        return False, "Registration failed."

    except Exception as e:
        return False, str(e)

def insert_record(table_name, payload):
    try:
        supabase.table(table_name).insert(payload).execute()
        return True, None
    except Exception as e:
        return False, str(e)

def get_all_users():
    try:
        # Select from 'app_users'
        res = supabase.table("app_users").select("*").execute()
        return res.data
    except:
        return []

def update_user_permissions(user_id, is_approved, allowed_modules, role):
    try:
        payload = {
            "is_approved": is_approved,
            "allowed_modules": allowed_modules,
            "role": role
        }
        # Update 'app_users'
        supabase.table("app_users").update(payload).eq("id", user_id).execute()
        return True
    except Exception as e:
        print(f"Update error: {e}")
        return False
