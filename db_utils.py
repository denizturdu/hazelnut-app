import streamlit as st
from supabase import create_client, Client
import bcrypt

# --- SUPABASE CONNECTION ---
# Secrets must be set in Streamlit Cloud -> Advanced Settings
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- AUTHENTICATION FUNCTIONS ---

def hash_password(password: str) -> str:
    """Converts a plain text password into a secure hash."""
    # bcrypt requires bytes, so we encode the string
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8') # Decode back to string for storage

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Checks if the plain password matches the hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def register_user(email, password, role='customer'):
    """Creates a new user in the database."""
    try:
        hashed = hash_password(password)
        
        # Employees are auto-approved (for now, or you can change this), Customers need approval
        is_approved = True if role == 'employee' else False
        
        data = {
            "email": email,
            "password_hash": hashed,
            "role": role,
            "is_approved": is_approved
        }
        
        response = supabase.table("app_users").insert(data).execute()
        return True, "Kayıt Başarılı! Onay bekleniyor."
    except Exception as e:
        return False, f"Hata: {e} (E-posta zaten kayıtlı olabilir)"

def login_user(email, password):
    """Verifies email/password and checks approval status."""
    try:
        # Fetch user by email
        response = supabase.table("app_users").select("*").eq("email", email).execute()
        
        if not response.data:
            return None, "Kullanıcı bulunamadı."
        
        user = response.data[0]
        
        # 1. Verify Password
        if verify_password(password, user['password_hash']):
            # 2. Check Approval
            if user['is_approved']:
                return user, "OK"
            else:
                return None, "Hesabınız henüz onaylanmadı. Lütfen yönetici ile iletişime geçin."
        else:
            return None, "Şifre hatalı."
            
    except Exception as e:
        return None, f"Giriş hatası: {e}"

# --- GENERIC DB INSERT ---
def insert_record(table_name, payload):
    data, count = supabase.table(table_name).insert(payload).execute()
    return data
