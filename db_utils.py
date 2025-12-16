import streamlit as st
from supabase import create_client, Client
import bcrypt

# --- SUPABASE CONNECTION ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- AUTHENTICATION ---

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def register_user(email, password, role='customer'):
    try:
        hashed = hash_password(password)
        # Default: No modules allowed, Not approved
        data = {
            "email": email,
            "password_hash": hashed,
            "role": role,
            "is_approved": False, 
            "allowed_modules": [] 
        }
        response = supabase.table("app_users").insert(data).execute()
        return True, "Kayıt Başarılı! Yönetici onayı bekleniyor."
    except Exception as e:
        return False, f"Hata: {e}"

def login_user(email, password):
    try:
        response = supabase.table("app_users").select("*").eq("email", email).execute()
        if not response.data: return None, "Kullanıcı bulunamadı."
        
        user = response.data[0]
        
        if verify_password(password, user['password_hash']):
            if user['is_approved']:
                return user, "OK"
            else:
                return None, "Hesabınız henüz onaylanmadı."
        else:
            return None, "Şifre hatalı."
    except Exception as e:
        return None, f"Giriş hatası: {e}"

# --- USER MANAGEMENT (NEW) ---

def get_all_users():
    """Fetches all users for the Admin panel."""
    response = supabase.table("app_users").select("*").order("created_at", desc=True).execute()
    return response.data

def update_user_permissions(user_id, is_approved, allowed_modules, role):
    """Updates approval status and module access."""
    try:
        supabase.table("app_users").update({
            "is_approved": is_approved,
            "allowed_modules": allowed_modules,
            "role": role
        }).eq("id", user_id).execute()
        return True
    except:
        return False

# --- GENERIC DB INSERT ---
def insert_record(table_name, payload):
    data, count = supabase.table(table_name).insert(payload).execute()
    return data
