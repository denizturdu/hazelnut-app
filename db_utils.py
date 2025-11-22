import streamlit as st
from supabase import create_client, Client

# Initialize connection
# We use st.secrets so we don't publish passwords in the code
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

def run_query(table_name):
    response = supabase.table(table_name).select("*").execute()
    return response.data

def insert_record(table_name, data_dict):
    response = supabase.table(table_name).insert(data_dict).execute()
    return response

# LOGIN FUNCTION
def login_user(email, password):
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return response.user
    except Exception as e:
        return None
