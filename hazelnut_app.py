{\rtf1\ansi\ansicpg1252\cocoartf2822
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import streamlit as st\
import pandas as pd\
from db_utils import supabase, login_user, run_query, insert_record\
import time\
\
st.set_page_config(page_title="Hazelnut Factory System", layout="wide")\
\
# --- LOGIN SYSTEM ---\
if 'user' not in st.session_state:\
    st.session_state.user = None\
\
def login_screen():\
    st.title("\uc0\u55357 \u56594  Factory Login")\
    email = st.text_input("Email")\
    password = st.text_input("Password", type="password")\
    if st.button("Log In"):\
        user = login_user(email, password)\
        if user:\
            st.session_state.user = user\
            st.success("Login Successful!")\
            time.sleep(1)\
            st.rerun()\
        else:\
            st.error("Invalid email or password")\
\
def logout():\
    supabase.auth.sign_out()\
    st.session_state.user = None\
    st.rerun()\
\
# --- MAIN APP LOGIC ---\
if not st.session_state.user:\
    login_screen()\
else:\
    # Sidebar\
    st.sidebar.write(f"Logged in as: \{st.session_state.user.email\}")\
    if st.sidebar.button("Log Out"):\
        logout()\
        \
    module = st.sidebar.radio("Select Module", ["1. Purchase", "2. Intake", "Admin Tools"])\
\
    # --- MODULE 1: PURCHASE ---\
    if module == "1. Purchase":\
        st.header("Module 1: Purchase")\
        \
        with st.form("new_purchase"):\
            supplier = st.text_input("Supplier Name")\
            item = st.selectbox("Item", ["Hazelnut (Levant)", "Hazelnut (Giresun)", "Jute Bags"])\
            qty = st.number_input("Quantity", min_value=1.0)\
            price = st.number_input("Unit Price", min_value=0.0)\
            \
            if st.form_submit_button("Create Contract"):\
                data = \{\
                    "supplier": supplier,\
                    "item": item,\
                    "qty_ordered": qty,\
                    "unit_price": price,\
                    "status": "Pending Arrival",\
                    "created_by": st.session_state.user.email\
                \}\
                # Send to Real DB\
                try:\
                    insert_record("purchases", data)\
                    st.success("Saved to Cloud Database!")\
                except Exception as e:\
                    st.error(f"Error: \{e\}")\
\
    # --- MODULE 2: INTAKE ---\
    elif module == "2. Intake":\
        st.header("Module 2: Intake")\
        st.subheader("Pending Arrivals")\
        \
        # Get Data from Real DB\
        try:\
            # We fetch all purchases where status is Pending\
            response = supabase.table("purchases").select("*").eq("status", "Pending Arrival").execute()\
            pending_items = response.data\
            \
            if pending_items:\
                df = pd.DataFrame(pending_items)\
                st.dataframe(df)\
            else:\
                st.info("No pending arrivals.")\
                \
        except Exception as e:\
            st.error("Database not ready yet. Go to Admin Tools to setup tables.")\
\
    # --- ADMIN TOOLS (First Time Setup) ---\
    elif module == "Admin Tools":\
        st.warning("Only use this to reset/create the database tables.")\
        if st.button("Create Database Tables"):\
            # This is a bit of a hack to create tables from Python, \
            # usually we do this in Supabase SQL Editor.\
            # But for now, we just check connectivity.\
            st.info("To create tables, please go to Supabase > SQL Editor and paste the script provided by your AI assistant.")}