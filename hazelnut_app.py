import streamlit as st
import pandas as pd
from db_utils import supabase, login_user, register_user, insert_record, get_all_users, update_user_permissions
import time
import io
import xlsxwriter
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests

st.set_page_config(page_title="Fındık Fabrikası Yönetimi", layout="wide")

# --- SESSION STATE SETUP ---
if 'user' not in st.session_state: st.session_state.user = None
if 'role' not in st.session_state: st.session_state.role = None
if 'offer_step' not in st.session_state: st.session_state.offer_step = "menu"
if 'offer_quality_data' not in st.session_state: st.session_state.offer_quality_data = {} 
if 'active_quality_row' not in st.session_state: st.session_state.active_quality_row = None
if 'generated_excel_data' not in st.session_state: st.session_state.generated_excel_data = None
if 'temp_custom_params' not in st.session_state: st.session_state.temp_custom_params = {}

# --- CONSTANTS ---
# Standardized Names with Numbers & Correct Language
# Group 1: Avella Turkiye (1, 2, 3, 5, 7)
# Group 2: Avella Management (4, 6)
MODULE_MAP = {
    1: "1. Şube Ürün Girişi",          # Turkish
    2: "2. Fabrika Ürün Girişi",       # Turkish
    3: "3. Üretim - Kırma",            # Turkish (Renamed from Mal Kabul)
    4: "4. Administrator Settings",    # English
    5: "5. Stok Takibi",               # Turkish
    6: "6. Offers",                    # English
    7: "7. Kalite Kontrol"             # Turkish
}

# Group 3: Partners
CUSTOMER_PORTAL_NAME = "🌍 Avella Customer Portal" # English

# Defined Groups for Sidebar Ordering
GROUP_TURKIYE = [1, 2, 3, 5, 7]
GROUP_MANAGEMENT = [4, 6]

CALIBRE_OPTIONS = [
    "Mixed Size", "21mm+", "20mm+", "19mm+", "18mm+", "17mm+", "16mm+", 
    "15-16mm", "14-15mm", "13-15mm", "13-14mm", "12-14mm", "12-13mm", 
    "11-13mm", "11-12mm", "10-12mm", "10-11mm", "9-11mm", "9-10mm", 
    "9mm-", "9mm+", "0-2mm", "1-3mm", "2-4mm", "4-6mm", "5-7mm", 
    "6-8mm", "7-11mm", "3-11mm", "5-11mm", "15μ", "18μ", "20μ", 
    "21μ", "22μ", "23μ", "24μ", "25μ", "26μ", "27μ", "28μ", "29μ", 
    "30μ", "31μ", "32μ", "33μ", "34μ", "35μ"
]

# --- OFFER MASTER DATA ---
OFFER_CONSTANTS = {
    "Categories": ["Nuts", "Dried Fruit", "Oil", "Chocolate"],
    "Product_Groups": ["Hazelnuts", "Walnuts", "Pistachios", "Almonds", "Peanuts", "Cashew Nuts", "Brazil Nuts", "Pine Nuts", "Macadamia Nuts", "Pecan Nuts", "Apricots", "Raisins", "Figs", "Plums", "Hazelnut Oil", "Olive Oil", "Hazelnut Cream", "Hazelnut Crunch", "Pistachio Cream", "Pistachio Crunch"],
    "Product_Types": ["Inshell", "Inshell - Harmanici", "Natural Kernels - Whole", "Natural Kernels - Shrivelled", "Natural Kernels - Scratched", "Natural Kernels - Broken", "Natural Kernels - Rotten", "Natural Kernels - Mix Reject", "Natural and Slivered", "Blanched Kernels - Whole", "Blanched and Chopped Pieces", "Blanched and Slivered", "Blanched and Diced", "Blanched and Scratched", "Blanched and Broken", "Blanched Flour", "Roasted Kernels - Whole", "Roasted and Chopped Pieces", "Roasted and Slivered", "Roasted and Diced", "Roasted and Scratched", "Roasted and Broken", "Roasted Flour", "Light Paste", "Dark Paste", "Medium Paste", "Shells"],
    "Varieties": ["Karışık", "Giresun Tombul", "Çakıldak", "Kara", "Sivri", "Palaz", "Badem", "Foşa", "Yomra", "Nonpareil", "Carmel", "Butte", "Padre", "Sonora", "Monterey", "Marcona", "Guara", "Kirmizi", "Uzun", "Halebi", "Siirt", "Ohadi", "Fandoghi", "Kalleh Ghouchi", "Ahmad Aghaei", "Akbari", "Kerman", "Golden Hills", "Lost Hills", "Kalehghouchi", "Gumdrop", "Chandler", "Hartley", "Howard", "Franquette", "Serr", "Tulare", "Pedro", "Şebin", "Bilecik", "Yalova", "Kaman", "Kaplan", "Şen", "Tokat"],
    "Sizes": ["Mixed Size", "21mm+", "20mm+", "19mm+", "18mm+", "17mm+", "16mm+", "14-16mm", "13-15mm", "15-16mm", "14-15mm", "13-14mm", "12-14mm", "12-13mm", "11-13mm", "11-12mm", "10-12mm", "10-11mm", "9-11mm", "9-10mm", "9mm-", "9mm+", "0-2mm", "1-3mm", "2-4mm", "4-6mm", "5-7mm", "6-8mm", "7-11mm", "3-11mm", "5-11mm", "15μ", "18μ", "20μ", "21μ", "22μ", "23μ", "24μ", "25μ", "26μ", "27μ", "28μ", "29μ", "30μ", "31μ", "32μ", "33μ", "34μ", "35μ", "18/20 mm", "20/22 mm", "22/24 mm", "24/26 mm", "26/28 mm", "28/30 mm", "30/32 mm", "32/34 mm", "34/36 mm", "36+ mm", "18/20 (US)", "20/22 (US)", "23/25 (US)", "25/27 (US)", "27/30 (US)", "30/32 (US)", "32/34 (US)", "34/36 (US)", "36/40 (US)", "40+ (US)", "Extra Large", "Large", "Medium", "Small"],
    "Packaging": ["Std Netted Bigbag (250-1000kg)", "Vacuum Bigbag (250-1000kg)", "Vac Bags in Carton (1-25kg)", "Alu Box (1-25kg)", "Nylon Sack (25-90kg)", "Gunny Sack (50-90kg)", "Tanker Truck", "Metal Drum (200L)", "Plastic Drum (60L)", "Plastic Bucket (1-25L)", "Metal Tin (5L)", "Retail Bag (Pillow)", "Retail Bag (Doybag)", "Retail Bag (Quadro)", "Glass Jar", "Small Bucket"],
    "Currencies": ["SEK", "TL", "USD", "EUR", "NOK"],
    "Incoterms": ["EXW", "FCA", "CPT", "CIP", "DAP", "DPU", "DDP", "FAS", "FOB", "CFR", "CIF"]
}

DEFAULT_QUALITY_PARAMS = {
    "Target Humidity %": "", "Maximum FFA %": 1, "Maximum Peroxide": 1, "Maximum Oversize %": 5,
    "Maximum Undersize %": 5, "Maximum Visible Rotten %": 2, "Maximum Hidden Rotten %": 2.5,
    "Maximum Visible Mouldy %": 0.5, "Maximum Hidden Mouldy %": 0.5, "Maximum Visible Tumorous %": 5,
    "Maximum Hidden Tumorous %": 5, "Maximum Insect Damaged %": 0, "Maximum Twin Kernels %": 2,
    "Maximum Mech. Damaged %": 8, "Maximum Broken %": 4, "Maximum Rancid %": 1,
    "Maximum Shrivelled %": 2.5, "Maximum Other Types %": 10, "Maximum Shell Pieces": "0.01%",
    "Maximum Foreign Matter": 0
}

# --- HELPER FUNCTIONS ---
def calculate_randiman(sample_w, good, shriv):
    if sample_w == 0: return 0.0
    return ((good + (shriv / 2)) / sample_w) * 100

def get_market_prices():
    try:
        response = supabase.table("market_prices").select("*").order("date", desc=False).limit(3000).execute()
        df = pd.DataFrame(response.data)
        if not df.empty: df['date'] = pd.to_datetime(df['date'])
        return df
    except: return pd.DataFrame()

def get_live_rates():
    rates = {"USD": 34.50, "EUR": 37.20} 
    try:
        url = "https://open.er-api.com/v6/latest/TRY"; resp = requests.get(url, timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            if "rates" in data:
                usd = data["rates"].get("USD"); eur = data["rates"].get("EUR")
                if usd: rates["USD"] = 1 / usd
                if eur: rates["EUR"] = 1 / eur
    except: pass
    return rates

def log_login(email):
    try: supabase.table("login_logs").insert({"email": email}).execute()
    except Exception as e: print(f"Login log error: {e}")

def get_product_specs():
    """Fetches defined product specifications from DB."""
    try:
        response = supabase.table("product_specs").select("*").execute()
        return response.data
    except: return []

def generate_offer_excel(header_data=None, product_df=None, quality_override=None):
    """Generates the Offer Excel file."""
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    workbook = writer.book
    worksheet = workbook.add_worksheet('Offer Sheet')
    worksheet.set_tab_color('#107C41')

    # Formats
    header_format = workbook.add_format({'bold': True, 'font_size': 14, 'color': '#203764'})
    label_format = workbook.add_format({'bold': True, 'align': 'right', 'bg_color': '#f2f2f2', 'border': 1})
    input_format = workbook.add_format({'border': 1, 'bg_color': '#ffffff'})
    table_header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1, 'text_wrap': True})
    linked_cell_format = workbook.add_format({'bg_color': '#E7E6E6', 'border': 1, 'italic': True, 'font_color': '#595959'})
    quality_header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#FFC000', 'font_color': 'black', 'border': 1, 'text_wrap': True})

    # Header
    worksheet.write('A1', 'AVELLA OFFER SHEET', header_format)
    headers = [("Date:", "B3", header_data.get("date", "")), ("Offer No:", "D3", header_data.get("offer_no", "")), ("Validity:", "F3", header_data.get("validity", "")), ("Customer Name:", "B4", header_data.get("customer", "")), ("Cust. Ref:", "D4", header_data.get("cust_ref", "")), ("Avella Ref:", "F4", header_data.get("avella_ref", "")), ("Payment Terms:", "B5", header_data.get("payment", "")), ("Delivery Addr:", "D5", header_data.get("delivery", ""))]
    for label, cell, val in headers:
        worksheet.write(cell, label, label_format); col_letter = cell[0]; row_num = int(cell[1:]); input_cell = chr(ord(col_letter) + 1) + str(row_num); worksheet.write(input_cell, str(val), input_format)
    worksheet.merge_range('E5:G5', "", input_format)

    # Product Table
    table_start_row = 8
    columns = ["Category", "Product Group", "Total Contract Volume (kg)", "Type/Process", "Variety", "Size", "Packaging", "Net Wgt (kg)", "Price", "Currency", "Incoterms", "Place of Delivery", "Minimum Order Quantity (kg)", "Shipment Schedule", "Payment Terms"]
    for i, col_name in enumerate(columns): worksheet.write(table_start_row, i, col_name, table_header_format); worksheet.set_column(i, i, 15)
    
    worksheet.set_column('B:B', 20); worksheet.set_column('C:C', 20); worksheet.set_column('D:D', 25); worksheet.set_column('E:E', 20); worksheet.set_column('G:G', 25); worksheet.set_column('L:L', 20); worksheet.set_column('M:M', 25); worksheet.set_column('N:N', 20); worksheet.set_column('O:O', 20)

    data_rows_count = 100
    if product_df is not None and not product_df.empty:
        valid_cols = [c for c in columns if c in product_df.columns]
        for idx, row in product_df.iterrows():
            row_num = table_start_row + 1 + idx
            for col_idx, col_name in enumerate(columns):
                val = row.get(col_name, "")
                worksheet.write(row_num, col_idx, val, input_format)
        data_rows_count = max(100, len(product_df) + 10)

    # Quality Sheet
    worksheet_qual = workbook.add_worksheet('Quality Parameters'); worksheet_qual.set_tab_color('#FFC000')
    qual_ident_cols = ["Product Group (Linked)", "Type (Linked)", "Variety (Linked)", "Size (Linked)"]
    qual_keys = list(DEFAULT_QUALITY_PARAMS.keys())
    all_qual_cols = qual_ident_cols + qual_keys

    for i, col_name in enumerate(all_qual_cols): worksheet_qual.write(table_start_row, i, col_name, quality_header_format); worksheet_qual.set_column(i, i, 22) 

    # Formulas & Values
    param_row_limit = 100
    if product_df is not None: param_row_limit = max(100, len(product_df) + 5)

    for r_idx in range(param_row_limit):
        xl_row = table_start_row + 1 + r_idx + 1
        worksheet_row = table_start_row + 1 + r_idx
        worksheet_qual.write_formula(worksheet_row, 0, f"='Offer Sheet'!B{xl_row}", linked_cell_format) 
        worksheet_qual.write_formula(worksheet_row, 1, f"='Offer Sheet'!D{xl_row}", linked_cell_format) 
        worksheet_qual.write_formula(worksheet_row, 2, f"='Offer Sheet'!E{xl_row}", linked_cell_format) 
        worksheet_qual.write_formula(worksheet_row, 3, f"='Offer Sheet'!F{xl_row}", linked_cell_format) 
        
        row_custom_data = {}
        if quality_override and r_idx in quality_override:
            row_custom_data = quality_override[r_idx]

        for i, key in enumerate(qual_keys):
            val = row_custom_data.get(key, DEFAULT_QUALITY_PARAMS.get(key, ""))
            worksheet_qual.write(worksheet_row, 4 + i, val, input_format)

    # Reference Data
    ref_sheet = workbook.add_worksheet('ReferenceData'); ref_sheet.hide()
    def write_list_to_ref(header, data_list, col_idx):
        ref_sheet.write(0, col_idx, header); [ref_sheet.write(i + 1, col_idx, item) for i, item in enumerate(data_list)]; return f"=ReferenceData!${xlsxwriter.utility.xl_col_to_name(col_idx)}$2:${xlsxwriter.utility.xl_col_to_name(col_idx)}${len(data_list) + 1}"
    
    cat_range = write_list_to_ref("Categories", OFFER_CONSTANTS["Categories"], 0); group_range = write_list_to_ref("Groups", OFFER_CONSTANTS["Product_Groups"], 1); type_range = write_list_to_ref("Types", OFFER_CONSTANTS["Product_Types"], 2); var_range = write_list_to_ref("Varieties", OFFER_CONSTANTS["Varieties"], 3); size_range = write_list_to_ref("Sizes", OFFER_CONSTANTS["Sizes"], 4); pack_range = write_list_to_ref("Packaging", OFFER_CONSTANTS["Packaging"], 5); curr_range = write_list_to_ref("Currencies", OFFER_CONSTANTS["Currencies"], 6); inco_range = write_list_to_ref("Incoterms", OFFER_CONSTANTS["Incoterms"], 7)
    
    val_end = table_start_row + 1 + data_rows_count
    worksheet.data_validation(table_start_row + 1, 0, val_end, 0, {'validate': 'list', 'source': cat_range})
    worksheet.data_validation(table_start_row + 1, 1, val_end, 1, {'validate': 'list', 'source': group_range})
    worksheet.data_validation(table_start_row + 1, 3, val_end, 3, {'validate': 'list', 'source': type_range})
    worksheet.data_validation(table_start_row + 1, 4, val_end, 4, {'validate': 'list', 'source': var_range})
    worksheet.data_validation(table_start_row + 1, 5, val_end, 5, {'validate': 'list', 'source': size_range})
    worksheet.data_validation(table_start_row + 1, 6, val_end, 6, {'validate': 'list', 'source': pack_range})
    worksheet.data_validation(table_start_row + 1, 9, val_end, 9, {'validate': 'list', 'source': curr_range})
    worksheet.data_validation(table_start_row + 1, 10, val_end, 10, {'validate': 'list', 'source': inco_range})

    writer.close(); output.seek(0); return output

# ==========================================
# 🔐 AUTHENTICATION PAGE
# ==========================================
if not st.session_state.user:
    st.title("🌰 Avella Giriş Paneli")
    tab_login, tab_register = st.tabs(["Giriş Yap (Login)", "Kayıt Ol (Register)"])
    with tab_login:
        email = st.text_input("E-posta", key="login_email")
        password = st.text_input("Şifre", type="password", key="login_pass")
        if st.button("Giriş Yap", type="primary"):
            user, msg = login_user(email, password)
            if user:
                log_login(user['email'])
                st.session_state.user = user; st.session_state.role = user['role']
                st.success(f"Hoşgeldiniz, {user['email']} ({user['role']})"); time.sleep(0.5); st.rerun()
            else: st.error(msg)
    with tab_register:
        st.caption("Sadece Müşteriler veya Yeni Personel için")
        new_email = st.text_input("E-posta", key="reg_email")
        new_pass = st.text_input("Şifre Belirleyin", type="password", key="reg_pass")
        new_pass_confirm = st.text_input("Şifre Tekrar", type="password", key="reg_pass2")
        reg_role = "customer"
        if "@avella" in new_email: st.info("Avella personeli olarak algılandı (Otomatik Onay)."); reg_role = "employee"
        if st.button("Kayıt Ol"):
            if new_pass != new_pass_confirm: st.error("Şifreler eşleşmiyor!")
            elif len(new_pass) < 6: st.error("Şifre en az 6 karakter olmalı.")
            else:
                success, msg = register_user(new_email, new_pass, role=reg_role)
                if success: st.success(msg)
                else: st.error(msg)

# ==========================================
# 🚀 MAIN APP (ROUTER LOGIC)
# ==========================================
else:
    user = st.session_state.user; role = st.session_state.role
    st.sidebar.info(f"👤 {user['email']}"); st.sidebar.caption(f"Rol: {role.upper()}")
    if st.sidebar.button("Çıkış Yap"): st.session_state.user = None; st.session_state.role = None; st.rerun()

    # --- DYNAMIC ROUTING & ORDERING ---
    # Constructing the menu based on the 3 Requested Groups
    available_menu_names = []
    
    # Check permissions helper
    def has_access(mod_id):
        if role == 'administrator': return True
        allowed = user.get('allowed_modules', [])
        return mod_id in allowed

    # 1. Avella Turkiye
    available_menu_names.append(MODULE_MAP[1]) if has_access(1) else None
    available_menu_names.append(MODULE_MAP[2]) if has_access(2) else None
    available_menu_names.append(MODULE_MAP[3]) if has_access(3) else None
    available_menu_names.append(MODULE_MAP[5]) if has_access(5) else None
    available_menu_names.append(MODULE_MAP[7]) if has_access(7) else None

    # 2. Avella Management
    available_menu_names.append(MODULE_MAP[4]) if has_access(4) else None
    available_menu_names.append(MODULE_MAP[6]) if has_access(6) else None
    
    # 3. Partners
    available_menu_names.append(CUSTOMER_PORTAL_NAME) # Everyone has portal

    if not available_menu_names: st.error("🚫 Yetkili olduğunuz modül bulunmamaktadır."); st.stop()
    module = st.sidebar.radio("Menü", available_menu_names)

    # ==========================
    # CUSTOMER PORTAL
    # ==========================
    if module == CUSTOMER_PORTAL_NAME:
        st.title(CUSTOMER_PORTAL_NAME)
        portal_tabs = ["Inshell Hazelnuts and Market Updates"]
        if role == 'administrator': portal_tabs.append("Avella Market Price Input (Admin)")
        tabs = st.tabs(portal_tabs)
        
        with tabs[0]:
            st.header("🌰 Market Updates & Inshell Prices")
            df_prices = get_market_prices()
            live_rates = get_live_rates()
            rate_usd_live = live_rates.get("USD", 34.0)
            rate_eur_live = live_rates.get("EUR", 37.0)
            with st.expander("Live Currency Rates (Auto-fetched)", expanded=True):
                c1, c2 = st.columns(2)
                c1.metric("USD/TRY", f"{rate_usd_live:.4f}")
                c2.metric("EUR/TRY", f"{rate_eur_live:.4f}")
            
            if not df_prices.empty:
                max_db_date = df_prices['date'].max()
                start_window = max_db_date - timedelta(days=365)
                colors = {"Tombul": "firebrick", "Cakildak": "royalblue", "Levant": "green"}
                st.markdown("---")
                def build_chart(title, mode_type, y_label):
                    fig = go.Figure()
                    for h_type in ["Tombul", "Cakildak", "Levant"]:
                        col_name = f"price_{h_type.lower()}"
                        if col_name in df_prices.columns:
                            if mode_type == 'TL': y_vals = df_prices[col_name]
                            elif mode_type == 'USD': y_vals = df_prices[col_name] / df_prices['rate_usd_try']
                            elif mode_type == 'EUR': y_vals = df_prices[col_name] / df_prices['rate_eur_try']
                            fig.add_trace(go.Scatter(x=df_prices['date'], y=y_vals, name=h_type, line=dict(color=colors[h_type], width=3), mode='lines', fill=None))
                    fig.update_layout(title=title, xaxis=dict(title="Date", rangeslider=dict(visible=True), type="date", range=[start_window, max_db_date]), yaxis=dict(title=dict(text=y_label, font=dict(color="black"))), hovermode="x unified", height=500)
                    return fig
                st.plotly_chart(build_chart("1. Inshell Prices (TL/kg)", 'TL', "Price (TL)"), use_container_width=True)
                st.plotly_chart(build_chart("2. Inshell Prices (USD/kg)", 'USD', "Price (USD)"), use_container_width=True)
                st.plotly_chart(build_chart("3. Inshell Prices (EUR/kg)", 'EUR', "Price (EUR)"), use_container_width=True)
            else: st.info("No market price data available yet.")

        if role == 'administrator' and len(tabs) > 1:
            with tabs[1]:
                st.header("📝 Input Daily Market Prices")
                live_rates = get_live_rates(); default_usd = live_rates.get("USD", 0.0); default_eur = live_rates.get("EUR", 0.0)
                with st.form("price_input_form"):
                    d_date = st.date_input("Date", value=datetime.now()); st.caption("Enter prices for ALL 3 types (TL/kg)."); c1, c2, c3 = st.columns(3); p_tombul = c1.number_input("Tombul", min_value=0.0, step=0.5); p_cakildak = c2.number_input("Cakildak", min_value=0.0, step=0.5); p_levant = c3.number_input("Levant", min_value=0.0, step=0.5)
                    st.markdown("---"); st.write("**Exchange Rates (Auto-fetched)**"); c4, c5 = st.columns(2); r_usd = c4.number_input("USD/TRY Rate", min_value=0.0, step=0.01, format="%.4f", value=default_usd); r_eur = c5.number_input("EUR/TRY Rate", min_value=0.0, step=0.01, format="%.4f", value=default_eur)
                    if st.form_submit_button("Save Entry"):
                        if p_tombul > 0 and p_cakildak > 0 and p_levant > 0:
                            payload = {"date": str(d_date), "price_tombul": p_tombul, "price_cakildak": p_cakildak, "price_levant": p_levant, "rate_usd_try": r_usd, "rate_eur_try": r_eur, "created_by": st.session_state.user['email']}
                            try: supabase.table("market_prices").upsert(payload, on_conflict="date").execute(); st.success("Entry Saved Successfully!"); time.sleep(1); st.rerun()
                            except Exception as e: st.error(f"Error: {e}")
                        else: st.warning("Please fill all price fields.")
                st.markdown("### 📜 Historical Data Input")
                df_hist = get_market_prices()
                if not df_hist.empty:
                    disp_cols = ["id", "date", "price_tombul", "price_cakildak", "price_levant", "rate_usd_try", "rate_eur_try", "created_by"]; valid_cols = [c for c in disp_cols if c in df_hist.columns]
                    st.dataframe(df_hist[valid_cols].sort_values(by='date', ascending=False).style.format({"price_tombul": "{:.2f}", "price_cakildak": "{:.2f}", "price_levant": "{:.2f}", "rate_usd_try": "{:.4f}", "rate_eur_try": "{:.4f}"}), use_container_width=True, hide_index=True)

    # ==========================
    # MODULE 1
    # ==========================
    elif module == MODULE_MAP[1]:
        st.title("Modül 1: Şube Ürün Girişi"); hazelnut_cat = "Kabuklu Fındık"; st.info("Bu modül Şubelerden yapılan **Kabuklu Fındık** alımları içindir."); 
        with st.form("sube_hazelnut_form"):
            st.subheader("1. Müstahsil & Tedarikçi"); c1, c2, c3 = st.columns(3); supplier = c1.text_input("Tedarikçi Adı"); sup_type = c2.selectbox("Tedarikçi Tipi", ["Müstahsil", "Tüccar", "Şirket"]); id_num = c3.text_input("TCKN / VKN"); c4, c5, c6 = st.columns(3); city = c4.text_input("İl"); dist_in = c5.text_input("İlçe"); vill_in = c6.text_input("Köy / Mahalle"); c_cont, c_cert = st.columns(2); contact = c_cont.text_input("Telefon No"); cert_status = c_cert.selectbox("Sertifikasyon", ["Yok", "Organik", "Rainforest Alliance", "Avella"]); st.markdown("---"); c7, c8, c9 = st.columns(3); reg_type = c7.selectbox("Alım Şekli", ["Satın Alma", "Emanet"]); location = c8.selectbox("Teslimat Yeri", ["Fabrika", "Tarla", "Avella Şube"]); hazelnut_type = c9.selectbox("Fındık Çeşidi", ["Karışık", "Giresun Tombul", "Çakıldak", "Kara", "Sivri", "Palaz", "Badem", "Foşa", "Yomra"]); st.markdown("---"); price_gross=0.0; price_net_deducted=0.0; val_randiman=0.0; st.subheader("2. Kalite, Miktar ve Fiyatlandırma"); col_q1, col_q2 = st.columns([1, 1])
            with col_q1: st.markdown("**Fiziksel Analiz (Eksper)**"); w_sample = st.number_input("Kabuklu Numune Ağırlığı (g)", value=250.0); w_good = st.number_input("Sağlam İç (g)", 0.0); w_shriv = st.number_input("Buruşuk İç (g)", 0.0); w_vis_rot = st.number_input("Görünen Çürük (g)", 0.0); w_hid_rot = st.number_input("Gizli Çürük (g)", 0.0); w_tumor = st.number_input("Ur (g)", 0.0); s1, s2 = st.columns(2); w_over = s1.number_input("1. Numara İç - 13 mm üzeri (g)", 0.0); w_under = s2.number_input("Elek Altı İç - 9 mm altı (g)", 0.0); val_moist = st.number_input("Nem (%)", 0.0, 100.0, 5.0)
            with col_q2: st.markdown("**Miktar ve Fiyatlandırma**"); net_weight = st.number_input("Toplam Net Ağırlık (kg)", min_value=0.0); st.caption("Paket Adetleri"); p1, p2, p3 = st.columns(3); cnt_nylon = p1.number_input("Naylon", min_value=0); cnt_jute = p2.number_input("Jüt", min_value=0); cnt_bigbag = p3.number_input("Big Bag", min_value=0); st.markdown("---"); 
            if reg_type == "Emanet": st.info("Emanet Alım: Fiyat 0 TL"); price_gross = 0.0
            else: price_gross = st.number_input("Borsa Fiyatı (50 Randıman)", value=120.0)
            st.markdown("---"); calc_pressed = st.form_submit_button("🔄 Randıman ve Fiyat Hesapla"); val_randiman = calculate_randiman(w_sample, w_good, w_shriv); net_price_50 = price_gross / 1.0245; unit_price = net_price_50 * (val_randiman / 50.0); total_val = unit_price * net_weight
            if calc_pressed: st.markdown("##### Analiz Sonuçları"); st.metric("Randıman", f"%{val_randiman:.2f}"); 
            if reg_type != "Emanet": st.success(f"💰 **TOPLAM TUTAR:** {total_val:,.2f} TL")
            st.markdown("---"); st.subheader("3. Ödeme ve Kayıt"); f1, f2, f3 = st.columns(3); doc_num = f1.text_input("Makbuz / Fatura No"); pay_amount = f2.number_input("Ödenen Tutar", 0.0); pay_method = f3.selectbox("Ödeme Yöntemi", ["Nakit", "Banka", "Çek"]); 
            if reg_type != "Emanet": st.metric("Kalan Bakiye", f"{total_val - pay_amount:,.2f} TL")
            if st.form_submit_button("✅ Şube Girişini Kaydet"):
                payload = {"created_by": st.session_state.user['email'], "status": "Pending Arrival", "category": hazelnut_cat, "supplier": supplier, "supplier_type": sup_type, "id_number": id_num, "city": city, "district": dist_in, "village": vill_in, "phone_number": contact, "cert_status": cert_status, "reg_type": reg_type, "location": location, "item_type": hazelnut_type, "qty_ordered": net_weight, "total_value": total_val, "document_number": doc_num, "payment_amount": pay_amount, "remaining_balance": total_val - pay_amount, "count_nylon": cnt_nylon, "count_jute": cnt_jute, "count_bigbag": cnt_bigbag, "weight_sample": w_sample, "weight_good": w_good, "weight_shrivelled": w_shriv, "weight_visible_rotten": w_vis_rot, "weight_hidden_rotten": w_hid_rot, "weight_tumor": w_tumor, "weight_undersize": w_under, "weight_oversize": w_over, "moisture": val_moist, "calculated_randiman": val_randiman, "gross_price_50": price_gross, "net_price_50": net_price_50, "actual_unit_price": unit_price}; insert_record("purchases", payload); st.success("Şube Girişi Kaydedildi!")
    elif module == MODULE_MAP[2]:
        st.title("Modül 2: Fabrika Ürün Girişi"); tab_findik, tab_malzeme, tab_genel = st.tabs(["🌰 Fındık Alımı", "📦 Malzeme Alımı", "⚙️ Makine & Hizmet"])
        with tab_findik:
            hazelnut_cat = st.selectbox("Fındık Kategorisi", ["Kabuklu Fındık", "İç Fındık", "İşlenmiş Fındık"], key="fab_findik_cat")
            with st.form("fab_hazelnut_form"):
                st.subheader("1. Müstahsil & Tedarikçi"); c1, c2, c3 = st.columns(3); supplier = c1.text_input("Tedarikçi Adı"); sup_type = c2.selectbox("Tedarikçi Tipi", ["Müstahsil", "Tüccar", "Şirket"]); id_num = c3.text_input("TCKN / VKN"); c4, c5, c6 = st.columns(3); city = c4.text_input("İl"); dist_in = c5.text_input("İlçe"); vill_in = c6.text_input("Köy / Mahalle"); c_cont, c_cert = st.columns(2); contact = c_cont.text_input("Telefon No"); cert_status = c_cert.selectbox("Sertifikasyon", ["Yok", "Organik", "Rainforest Alliance", "Avella"]); st.markdown("---"); c7, c8, c9 = st.columns(3); reg_type = c7.selectbox("Alım Şekli", ["Satın Alma", "Emanet"]); location = c8.selectbox("Teslimat Yeri", ["Fabrika", "Tarla", "Avella Şube"]); hazelnut_type = c9.selectbox("Fındık Çeşidi", ["Karışık", "Giresun Tombul", "Çakıldak", "Kara", "Sivri", "Palaz", "Badem", "Foşa", "Yomra"]); st.markdown("---"); st.subheader("2. Detaylı Kalite Analizi (Laboratuvar)"); k1, k2, k3 = st.columns(3); label_sample = "Kabuklu Numune Ağırlığı (g)" if hazelnut_cat == "Kabuklu Fındık" else "İç Numune Ağırlığı (g)"; w_sample = k1.number_input(label_sample, value=250.0 if hazelnut_cat == "Kabuklu Fındık" else 100.0); lab_cal = k2.selectbox("Kalibre", CALIBRE_OPTIONS); val_moist = k3.number_input("Nem (%)", 0.0, 100.0, 5.0); k4, k5 = st.columns(2); l_ffa = k4.number_input("FFA (%)", 0.0, 100.0, 0.0); l_perox = k5.number_input("Peroksit (meqO2/kg)", 0.0); st.markdown("##### B. Fiziksel Kusurlar (Gram)"); r1c1, r1c2, r1c3, r1c4 = st.columns(4); w_good = r1c1.number_input("Sağlam İç (g)", 0.0); w_vis_rot = r1c2.number_input("Görünen Çürük (g)", 0.0); w_hid_rot = r1c3.number_input("Gizli Çürük (g)", 0.0); w_worm = r1c4.number_input("Kurt Yenikli (g)", 0.0); r2c1, r2c2, r2c3, r2c4 = st.columns(4); w_vis_mold = r2c1.number_input("Görünen Küflü (g)", 0.0); w_hid_mold = r2c2.number_input("Gizli Küflü (g)", 0.0); w_vis_tumor = r2c3.number_input("Görünen Urlu (g)", 0.0); w_hid_tumor = r2c4.number_input("Gizli Urlu (g)", 0.0); r3c1, r3c2, r3c3, r3c4 = st.columns(4); w_shriv = r3c1.number_input("Buruşuk İç (g)", 0.0); w_lemon = r3c2.number_input("Limoni (g)", 0.0); w_decayed = r3c3.number_input("Vurgun (g)", 0.0); w_broken = r3c4.number_input("Kırık (g)", 0.0); r4c1, r4c2, r4c3, r4c4 = st.columns(4); w_twin = r4c1.number_input("İkiz (g)", 0.0); w_other = r4c2.number_input("Diğer Tipler (g)", 0.0); w_under = r4c3.number_input("Elek Altı (g)", 0.0); w_over = r4c4.number_input("Elek Üstü (g)", 0.0); st.markdown("##### C. Yabancı Madde & Mikrobiyolojik"); m1, m2, m3, m4 = st.columns(4); c_membrane = m1.number_input("Zar Atmayan Tane (adet)", 0); w_shell = m2.number_input("Kabuk (g)", 0.0); c_foreign = m3.number_input("Yabancı Madde (tane)", 0); size_1_g = 0.0; undersize_g = 0.0
                if hazelnut_cat == "Kabuklu Fındık": st.markdown("##### D. Kabuklu Ekstra Boylama (Gram)"); ex1, ex2 = st.columns(2); size_1_g = ex1.number_input("1. Numara İç - 13 mm üzeri (g)", 0.0); undersize_g = ex2.number_input("Elek Altı İç - 9 mm altı (g)", 0.0)
                st.markdown("---"); m_row2_1, m_row2_2, m_row2_3, m_row2_4 = st.columns(4); l_salm = m_row2_1.text_input("Salmonella"); l_ecoli = m_row2_2.text_input("E. Coli"); l_b1 = m_row2_3.number_input("Aflatoksin B1 (ppb)", 0.0); l_tot = m_row2_4.number_input("Aflatoksin Total (ppb)", 0.0)
                st.markdown("---"); calc_btn = st.form_submit_button("📊 Rapor Oluştur"); val_randiman = calculate_randiman(w_sample, w_good, w_shriv)
                if calc_btn: st.info("📊 **Canlı Analiz Raporu**"); calc_inputs = {"Sağlam İç": w_good, "Görünen Çürük": w_vis_rot, "Gizli Çürük": w_hid_rot, "Görünen Küflü": w_vis_mold, "Gizli Küflü": w_hid_mold, "Görünen Urlu": w_vis_tumor, "Gizli Urlu": w_hid_tumor, "Kurt Yenikli": w_worm, "Buruşuk İç": w_shriv, "Limoni": w_lemon, "Vurgun": w_decayed, "Kırık": w_broken, "İkiz": w_twin, "Diğer Tipler": w_other, "Elek Altı": w_under, "Elek Üstü": w_over, "Kabuk": w_shell}; report_data = []
                if w_sample > 0 and calc_btn:
                    for k, v in calc_inputs.items():
                        pct = (v / w_sample) * 100; 
                        if v > 0: report_data.append({"Parametre": k, "Girdi (g)": f"{v} g", "Sonuç": f"%{pct:.2f}"})
                    if hazelnut_cat == "Kabuklu Fındık":
                        if size_1_g > 0: report_data.append({"Parametre": "1. Numara (13mm+)", "Girdi (g)": f"{size_1_g} g", "Sonuç": f"%{(size_1_g/w_sample)*100:.2f}"})
                        if undersize_g > 0: report_data.append({"Parametre": "Elek Altı (9mm-)", "Girdi (g)": f"{undersize_g} g", "Sonuç": f"%{(undersize_g/w_sample)*100:.2f}"})
                    if val_moist > 0: report_data.append({"Parametre": "Nem", "Girdi (g)": "-", "Sonuç": f"%{val_moist}"})
                    if l_ffa > 0: report_data.append({"Parametre": "FFA", "Girdi (g)": "-", "Sonuç": f"%{l_ffa}"})
                    if l_perox > 0: report_data.append({"Parametre": "Peroksit", "Girdi (g)": "-", "Sonuç": f"{l_perox} meq"})
                    st.dataframe(pd.DataFrame(report_data), use_container_width=True)
                st.markdown("---"); st.subheader("Miktar ve Fiyatlandırma"); cq1, cq2 = st.columns(2)
                with cq1: net_weight = st.number_input("Toplam Net Ağırlık (kg)", min_value=0.0); st.caption("Paketleme Detayları"); p1, p2, p3 = st.columns(3); cnt_nylon = p1.number_input("Naylon", min_value=0); cnt_jute = p2.number_input("Jüt", min_value=0); cnt_bigbag = p3.number_input("Big Bag", min_value=0)
                if reg_type == "Emanet": total_val = 0.0; price_gross = 0.0; price_net_deducted = 0.0
                else:
                    with cq2:
                        if hazelnut_cat == "Kabuklu Fındık": price_gross = st.number_input("Borsa Fiyatı (50 Randıman)", value=120.0); net_price_50 = price_gross / 1.0245; price_net_deducted = net_price_50 * (val_randiman / 50.0); 
                        else: price_gross = st.number_input("Gösterge Fiyatı (TL)", min_value=0.0); price_net_deducted = st.number_input("Net Fiyat (TL)", min_value=0.0)
                        total_val = price_net_deducted * net_weight; st.success(f"**TOPLAM TUTAR:** {total_val:,.2f} TL")
                st.markdown("---"); st.subheader("3. Ödeme ve Kayıt"); f1, f2, f3 = st.columns(3); doc_num = f1.text_input("Makbuz / Fatura No"); pay_amount = f2.number_input("Ödenen Tutar", 0.0); pay_method = f3.selectbox("Ödeme Yöntemi", ["Nakit", "Banka", "Çek"]); 
                if reg_type != "Emanet": st.metric("Kalan Bakiye", f"{total_val - pay_amount:,.2f} TL")
                if st.form_submit_button("✅ Fabrika Girişini Kaydet"):
                    payload = {"created_by": st.session_state.user['email'], "status": "Pending Arrival", "category": hazelnut_cat, "supplier": supplier, "supplier_type": sup_type, "id_number": id_num, "city": city, "district": dist_in, "village": vill_in, "phone_number": contact, "cert_status": cert_status, "reg_type": reg_type, "location": location, "item_type": hazelnut_type, "qty_ordered": net_weight, "total_value": total_val, "document_number": doc_num, "payment_amount": pay_amount, "remaining_balance": total_val - pay_amount, "count_nylon": cnt_nylon, "count_jute": cnt_jute, "count_bigbag": cnt_bigbag, "weight_sample": w_sample, "weight_good": w_good, "weight_shrivelled": w_shriv, "weight_visible_rotten": w_vis_rot, "weight_hidden_rotten": w_hid_rot, "weight_tumor": w_tumor, "weight_undersize": w_under, "weight_oversize": w_over, "moisture": val_moist, "calculated_randiman": val_randiman, "gross_price_50": price_gross, "actual_unit_price": price_net_deducted}; insert_record("purchases", payload); st.success("Fabrika Girişi Kaydedildi!")
        with tab_malzeme:
            st.subheader("Malzeme Seçimi"); material_cats = ["Ambalaj Malzemeleri", "Bakım Malzemeleri", "Ofis Malzemeleri", "Temizlik Malzemeleri", "Eşantiyon & Hediye", "İş Kıyafetleri", "Gıda ve Mutfak", "Diğer"]; c_cat, c_item = st.columns(2); selected_mat_cat = c_cat.selectbox("Kategori", material_cats, key="mat_cat_fab"); 
            try: response = supabase.table("material_definitions").select("*").eq("category", selected_mat_cat).execute(); items_data = response.data; item_names = [row['item_name'] for row in items_data]
            except: items_data = []; item_names = []
            if item_names: selected_item_name = c_item.selectbox("Malzeme Seç", item_names, key="mat_item_fab"); selected_item_data = next((item for item in items_data if item["item_name"] == selected_item_name), None)
            else: c_item.warning("Tanımlı malzeme yok."); selected_item_name = c_item.text_input("Manuel Giriş", key="mat_manual_fab")
            with st.form("fab_material_purchase"): 
                supplier = st.text_input("Tedarikçi"); c3, c4 = st.columns(2); qty = c3.number_input("Miktar", min_value=1.0); price = c4.number_input("Tutar (TL)", min_value=0.0); 
                if st.form_submit_button("✅ Kaydet"): payload = {"category": "Malzeme", "supplier": supplier, "item_type": selected_item_name, "item_sub_type": selected_mat_cat, "qty_ordered": qty, "total_value": price, "status": "Pending Arrival", "created_by": st.session_state.user['email']}; insert_record("purchases", payload); st.success("Kaydedildi!")
        with tab_genel:
            st.subheader("Genel Alım"); general_type = st.selectbox("Tür", ["Makine", "Hizmet"], key="gen_type_fab"); 
            with st.form("fab_gen_form"): 
                c1, c2 = st.columns(2); supplier = c1.text_input("Firma"); desc = c2.text_input("Açıklama"); c3, c4 = st.columns(2); qty = c3.number_input("Miktar", 1.0); price = c4.number_input("Tutar", 0.0); 
                if st.form_submit_button("✅ Kaydet"): insert_record("purchases", {"category": general_type, "supplier": supplier, "item_type": desc, "qty_ordered": qty, "total_value": price, "status": "Pending Arrival", "created_by": st.session_state.user['email']}); st.success("Kaydedildi!")

    # ==========================
    # MODULE 3: Üretim - Kırma (Turkish)
    # ==========================
    elif module == MODULE_MAP[3]:
        st.title("Modül 3: Üretim - Kırma"); 
        try:
            response = supabase.table("purchases").select("*").eq("status", "Pending Arrival").execute(); pending_df = pd.DataFrame(response.data)
            if not pending_df.empty:
                st.dataframe(pending_df[["id", "supplier", "item_type", "qty_ordered", "location"]]); po_ids = pending_df['id'].tolist(); selected_id = st.selectbox("Sipariş Seç (ID)", po_ids); row = pending_df[pending_df['id'] == selected_id].iloc[0]; st.info(f"Giriş: {row['item_type']} - {row['supplier']}")
                with st.form("intake"): c1, c2 = st.columns(2); plate = c1.text_input("Plaka"); waybill = c2.text_input("İrsaliye"); qty = st.number_input("Kantar Net", value=float(row['qty_ordered'] or 0)); loc = st.text_input("Depo"); 
                if st.form_submit_button("Onayla"): supabase.table("purchases").update({"status": "Received"}).eq("id", selected_id).execute(); insert_record("intake_log", {"po_id": int(selected_id), "plate_number": plate, "waybill_no": waybill, "received_qty": qty, "location_in_warehouse": loc, "created_by": st.session_state.user['email']}); insert_record("stock_movements", {"item_name": row['item_type'], "category": row.get('category'), "quantity": qty, "move_type": "Intake", "location": loc, "created_by": st.session_state.user['email']}); st.success("Giriş Yapıldı!"); time.sleep(1); st.rerun()
            else: st.info("Bekleyen yok.")
        except Exception as e: st.error(f"Hata: {e}")

    # ==========================
    # MODULE 4: Administrator (English)
    # ==========================
    elif module == MODULE_MAP[4]:
        st.title("🛠️ Administrator Settings")
        tab_users, tab_mat, tab_logs = st.tabs(["👥 User Permissions and Approval", "📦 Material Definitions", "📜 Login Logs"])
        
        with tab_users:
            st.subheader("User Permissions and Approval")
            
            # --- CREATE USER SECTION ---
            with st.expander("➕ Create New User (Manually)", expanded=False):
                with st.form("create_user_admin"):
                    st.write("**New User Details**")
                    c_new_email = st.text_input("Email")
                    c_new_pass = st.text_input("Password", type="password")
                    c_new_role = st.selectbox("Role", ["employee", "administrator", "customer"])
                    
                    st.write("**Initial Module Access:**")
                    new_mods = []
                    mod_keys = sorted(MODULE_MAP.keys())
                    cols = st.columns(2)
                    
                    for i, mod_id in enumerate(mod_keys):
                        target_col = cols[i % 2]
                        if target_col.checkbox(MODULE_MAP[mod_id], key=f"new_mod_{mod_id}"):
                            new_mods.append(mod_id)

                    if st.form_submit_button("Create User"):
                        if c_new_email and c_new_pass:
                            success, msg = register_user(c_new_email, c_new_pass, role=c_new_role)
                            if success:
                                time.sleep(1) 
                                new_user_data = supabase.table("users").select("id").eq("email", c_new_email).execute()
                                if new_user_data.data:
                                    uid = new_user_data.data[0]['id']
                                    update_user_permissions(uid, True, new_mods, c_new_role)
                                    st.success(f"User {c_new_email} created.")
                                time.sleep(1)
                                st.rerun()
                            else: st.error(msg)
                        else: st.warning("Email and Password required.")

            st.markdown("---")
            all_users = get_all_users()
            df_users = pd.DataFrame(all_users)
            
            if not df_users.empty:
                st.dataframe(df_users[['email', 'role', 'is_approved', 'allowed_modules']], use_container_width=True)
                st.markdown("---")
                user_list = {u['email']: u for u in all_users}
                selected_email = st.selectbox("Edit Existing User", list(user_list.keys()))
                
                if selected_email:
                    target_user = user_list[selected_email]
                    with st.form("edit_user_perm"):
                        st.write(f"**Editing:** {target_user['email']}")
                        current_role = target_user['role']
                        role_options = ["customer", "employee", "administrator"]
                        role_idx = role_options.index(current_role) if current_role in role_options else 0
                        new_role = st.selectbox("Role", role_options, index=role_idx)
                        new_approved = st.checkbox("Account Approved", value=target_user['is_approved'])
                        current_modules = target_user.get('allowed_modules') or []
                        
                        st.write("**Access Rights:**")
                        updated_mods = []
                        mod_keys = sorted(MODULE_MAP.keys())
                        cols = st.columns(2)
                        
                        for i, mod_id in enumerate(mod_keys):
                            target_col = cols[i % 2]
                            is_checked = mod_id in current_modules
                            if target_col.checkbox(MODULE_MAP[mod_id], value=is_checked, key=f"edit_mod_{mod_id}"):
                                updated_mods.append(mod_id)
                        
                        if st.form_submit_button("💾 Update Permissions"):
                            update_user_permissions(target_user['id'], new_approved, updated_mods, new_role)
                            st.success("Updated!")
                            time.sleep(1)
                            st.rerun()

        with tab_mat:
            cats = ["Ambalaj Malzemeleri", "Bakım Malzemeleri", "Ofis Malzemeleri", "Temizlik Malzemeleri", "Eşantiyon & Hediye", "İş Kıyafetleri", "Gıda ve Mutfak", "Diğer"]; units = ['adet', 'gr', 'kg', 'bobin', 'rulo', 'paket', 'deste', 'palet', 'litre', 'mililitre', 'metreküp', 'desimetreküp', 'santimetreküp', 'metre', 'desimetre', 'santimetre', 'milimetre', 'bigbag', 'kamyon', 'tır', 'tank', 'metrekare', 'santimetrekare', 'ar', 'dekar', 'hektar']; 
            with st.expander("Listeyi Gör"): data = supabase.table("material_definitions").select("*").execute().data; st.dataframe(pd.DataFrame(data), use_container_width=True)
            st.markdown("---"); st.write("### ➕ Ekle / ✏️ Düzenle / 🗑️ Sil"); action = st.radio("İşlem", ["Ekle", "Düzenle", "Sil"], horizontal=True)
            if action == "Ekle":
                with st.form("add_mat"): 
                    c1, c2 = st.columns(2); cat = c1.selectbox("Kategori", cats); name = c2.text_input("Ad"); u1, u2 = st.columns(2); unit = u1.selectbox("Birim", units); uq = u2.number_input("Birim İçi Adet", 1.0); nt = st.text_area("Notlar"); o1, o2, o3 = st.columns(3); dim_o = o1.text_input("Dış Boyutlar"); dim_i = o2.text_input("İç Boyutlar"); w_g = o3.number_input("Ağırlık (g)", 0.0); g1, g2, g3 = st.columns(3); use = g1.text_input("Kullanım"); mat = g2.text_input("Materyal"); oth = g3.text_input("Diğer"); 
                    if st.form_submit_button("Kaydet"): insert_record("material_definitions", {"category": cat, "item_name": name, "sales_unit": unit, "unit_quantity": uq, "notes": nt, "dim_outer": dim_o, "dim_inner": dim_i, "unit_weight_g": w_g, "use_case": use, "mat_type": mat, "other_specs": oth}); st.success("Eklendi!")
            elif action == "Düzenle":
                sel_cat = st.selectbox("Kategori", cats); items = supabase.table("material_definitions").select("*").eq("category", sel_cat).execute().data
                if items:
                    target = st.selectbox("Malzeme", [i['item_name'] for i in items]); row = next(i for i in items if i['item_name'] == target); 
                    with st.form("edit_mat"): 
                        new_name = st.text_input("Ad", row['item_name']); e1, e2, e3 = st.columns(3); emat = e1.text_input("Materyal", row.get('mat_type')); euse = e2.text_input("Kullanım", row.get('use_case')); eunit = e3.selectbox("Birim", units, index=units.index(row.get('sales_unit')) if row.get('sales_unit') in units else 0); enote = st.text_area("Notlar", row.get('notes')); 
                        if st.form_submit_button("Güncelle"): supabase.table("material_definitions").update({"item_name": new_name, "mat_type": emat, "use_case": euse, "sales_unit": eunit, "notes": enote}).eq("id", row['id']).execute(); st.success("Güncellendi!")
            elif action == "Sil":
                sel_cat = st.selectbox("Kategori (Sil)", cats); items = supabase.table("material_definitions").select("*").eq("category", sel_cat).execute().data
                if items:
                    target = st.selectbox("Silinecek", [i['item_name'] for i in items]); 
                    if st.button("Sil"): supabase.table("material_definitions").delete().eq("item_name", target).execute(); st.success("Silindi!")
        with tab_logs:
            st.markdown("### 📜 Sistem Giriş Kayıtları")
            try:
                logs_response = supabase.table("login_logs").select("*").order("login_at", desc=True).limit(1000).execute()
                if logs_response.data:
                    df_logs = pd.DataFrame(logs_response.data)
                    df_logs['login_at'] = pd.to_datetime(df_logs['login_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
                    df_logs.rename(columns={"email": "Kullanıcı", "login_at": "Tarih/Saat"}, inplace=True)
                    st.dataframe(df_logs[["Kullanıcı", "Tarih/Saat"]], use_container_width=True)
                else: st.info("Henüz kayıt bulunmamaktadır.")
            except Exception as e: st.error(f"Loglar yüklenirken hata oluştu: {e}")

    # ==========================
    # MODULE 5: Stok Takibi (Turkish)
    # ==========================
    elif module == MODULE_MAP[5]:
        st.title("📦 Stok Takibi"); moves = supabase.table("stock_movements").select("*").execute().data; df = pd.DataFrame(moves)
        if not df.empty: stock = df.groupby('item_name')['quantity'].sum().reset_index(); st.dataframe(stock, use_container_width=True); st.markdown("---"); st.dataframe(df.sort_values(by='created_at', ascending=False))
        else: st.info("Hareket yok.")

    # ==========================
    # MODULE 6: Offers (English)
    # ==========================
    elif module == MODULE_MAP[6]:
        st.title("📄 Offers")
        
        if st.session_state.offer_step == "menu":
            if st.button("➕ Create New Offer", type="primary"):
                st.session_state.offer_step = "create"
                st.rerun()
            st.info("Click above to start a new offer.")

        elif st.session_state.offer_step == "create":
            if st.button("⬅️ Back to Menu"):
                st.session_state.offer_step = "menu"
                st.rerun()
            st.markdown("### 📝 Offer Details & Product List")
            with st.container():
                c1, c2, c3 = st.columns(3)
                date_val = c1.date_input("Date", value=datetime.now())
                offer_no = c2.text_input("Offer No")
                validity = c3.text_input("Validity")
                c4, c5, c6 = st.columns(3)
                customer = c4.text_input("Customer Name")
                cust_ref = c5.text_input("Cust. Ref")
                avella_ref = c6.text_input("Avella Ref")
                c7, c8 = st.columns(2)
                payment = c7.text_input("Payment Terms")
                delivery = c8.text_input("Delivery Address")
            st.markdown("---")
            if 'offer_rows' not in st.session_state:
                st.session_state.offer_rows = pd.DataFrame([{"Quality Parameters": "Default", "Category": "Nuts", "Product Group": "Hazelnuts", "Total Contract Volume (kg)": 0, "Type/Process": "Natural Kernels - Whole", "Variety": "Levant", "Size": "11-13mm", "Packaging": "Bigbag", "Net Wgt (kg)": 1000, "Price": 0.0, "Currency": "USD", "Incoterms": "FCA", "Place of Delivery": "Istanbul", "Minimum Order Quantity (kg)": 1000, "Shipment Schedule": "Prompt", "Payment Terms": "CAD"}],)
            column_config = {
                "Quality Parameters": st.column_config.SelectboxColumn("Quality Parameters", options=["Default", "Edit...", "Updated"], required=True, width="small", help="Select 'Edit...' to modify"),
                "Category": st.column_config.SelectboxColumn("Category", options=OFFER_CONSTANTS["Categories"], required=True),
                "Product Group": st.column_config.SelectboxColumn("Group", options=OFFER_CONSTANTS["Product_Groups"], required=True),
                "Type/Process": st.column_config.SelectboxColumn("Type", options=OFFER_CONSTANTS["Product_Types"], required=True, width="medium"),
                "Variety": st.column_config.SelectboxColumn("Variety", options=OFFER_CONSTANTS["Varieties"], required=True),
                "Size": st.column_config.SelectboxColumn("Size", options=OFFER_CONSTANTS["Sizes"], required=True),
                "Packaging": st.column_config.SelectboxColumn("Packaging", options=OFFER_CONSTANTS["Packaging"], required=True, width="medium"),
                "Currency": st.column_config.SelectboxColumn("Currency", options=OFFER_CONSTANTS["Currencies"], required=True, width="small"),
                "Incoterms": st.column_config.SelectboxColumn("Incoterms", options=OFFER_CONSTANTS["Incoterms"], required=True, width="small"),
                "Total Contract Volume (kg)": st.column_config.NumberColumn("Vol (kg)", min_value=0),
                "Net Wgt (kg)": st.column_config.NumberColumn("Net Wgt", min_value=0),
                "Price": st.column_config.NumberColumn("Price", min_value=0.0, format="%.2f"),
            }
            edited_df = st.data_editor(st.session_state.offer_rows, column_config=column_config, num_rows="dynamic", use_container_width=True, key="offer_editor")
            rows_to_edit = edited_df.index[edited_df["Quality Parameters"] == "Edit..."].tolist()
            if rows_to_edit:
                target_idx = rows_to_edit[0]
                prev_status = "Updated" if target_idx in st.session_state.offer_quality_data else "Default"
                edited_df.at[target_idx, "Quality Parameters"] = prev_status
                st.session_state.offer_rows = edited_df
                st.session_state.active_quality_row = target_idx
                st.session_state.offer_step = "edit_quality"
                st.rerun()
            else:
                st.session_state.offer_rows = edited_df
            st.markdown("---")
            if st.button("Prepare & Export Offer", type="primary"):
                header_payload = {"date": date_val, "offer_no": offer_no, "validity": validity, "customer": customer, "cust_ref": cust_ref, "avella_ref": avella_ref, "payment": payment, "delivery": delivery}
                with st.spinner("Generating Excel..."):
                    excel_data = generate_offer_excel(header_data=header_payload, product_df=st.session_state.offer_rows, quality_override=st.session_state.offer_quality_data)
                    st.session_state.generated_excel_data = excel_data
                    st.success("Offer Generated!")
            if st.session_state.generated_excel_data:
                st.download_button(label="📥 Download Excel File", data=st.session_state.generated_excel_data, file_name=f"Avella_Offer_{offer_no if offer_no else 'Draft'}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        elif st.session_state.offer_step == "edit_quality":
            row_idx = st.session_state.active_quality_row
            if row_idx is None or row_idx >= len(st.session_state.offer_rows):
                st.session_state.offer_step = "create"
                st.rerun()
            row_data = st.session_state.offer_rows.iloc[row_idx]
            current_prod_type = row_data['Type/Process']
            st.warning(f"🔧 Editing Quality Parameters for Row #{row_idx + 1}")
            st.write(f"**Product:** {row_data['Product Group']} | {current_prod_type} | {row_data['Variety']} | {row_data['Size']}")
            
            all_specs = get_product_specs()
            relevant_specs = [s for s in all_specs if s.get('product_type') == current_prod_type]
            spec_options = {f"{s['spec_name']} ({s['product_type']})": s['parameters'] for s in all_specs}
            display_keys = [f"{s['spec_name']} ({s['product_type']})" for s in relevant_specs]
            other_keys = [k for k in spec_options.keys() if k not in display_keys]
            final_options = ["(Select to Load)"] + display_keys + ["--- Other Types ---"] + other_keys
            selected_template = st.selectbox("📥 Load from Specification Template", final_options)
            
            if selected_template and selected_template not in ["(Select to Load)", "--- Other Types ---"]:
                st.session_state.offer_quality_data[row_idx] = spec_options[selected_template]
                st.success(f"Loaded template: {selected_template}")
            
            current_vals = st.session_state.offer_quality_data.get(row_idx, DEFAULT_QUALITY_PARAMS.copy())
            
            with st.form("quality_form"):
                cols = st.columns(4)
                new_vals = {}
                all_keys = list(set(list(DEFAULT_QUALITY_PARAMS.keys()) + list(current_vals.keys())))
                def sort_key(k):
                    if k in DEFAULT_QUALITY_PARAMS: return list(DEFAULT_QUALITY_PARAMS.keys()).index(k)
                    return 999
                all_keys.sort(key=sort_key)

                for i, k in enumerate(all_keys):
                    col = cols[i % 4]
                    default_val = current_vals.get(k, "")
                    if isinstance(default_val, (int, float)):
                        new_vals[k] = col.number_input(k, value=float(default_val))
                    else:
                        new_vals[k] = col.text_input(k, value=str(default_val))
                
                st.markdown("---")
                if st.form_submit_button("✅ Save Parameters & Return"):
                    st.session_state.offer_quality_data[row_idx] = new_vals
                    st.session_state.offer_rows.at[row_idx, "Quality Parameters"] = "Updated"
                    st.session_state.offer_step = "create"
                    st.rerun()

    # ==========================
    # MODULE 7: Kalite Kontrol (Turkish)
    # ==========================
    elif module == MODULE_MAP.get(7): 
        st.title("🛡️ Kalite Kontrol & Spesifikasyonlar")
        
        tab_create, tab_list = st.tabs(["➕ Yeni Spesifikasyon Tanımla", "📜 Spesifikasyon Listesi / Güncelleme"])
        
        with tab_create:
            st.markdown("### Yeni Ürün Spesifikasyonu Tanımla")
            with st.expander("Özel Parametre Ekle (İsteğe Bağlı)"):
                c_custom1, c_custom2, c_custom3, c_custom4 = st.columns([2, 2, 2, 1])
                new_p_name = c_custom1.text_input("Parametre Adı")
                new_p_type = c_custom2.text_input("Parametre Tipi (Bilgi)")
                new_p_val = c_custom3.text_input("Varsayılan Değer")
                if c_custom4.button("Ekle"):
                    if new_p_name:
                        st.session_state.temp_custom_params[new_p_name] = new_p_val
                        st.success(f"{new_p_name} eklendi")
                    else:
                        st.error("İsim gerekli")
            
            if st.session_state.temp_custom_params:
                st.write("Eklenen Özel Parametreler:", st.session_state.temp_custom_params)

            with st.form("new_spec_form"):
                c1, c2 = st.columns(2)
                spec_name = c1.text_input("Spesifikasyon Adı (ör. 'Std Naturel 11-13')")
                prod_type = c2.selectbox("İlgili Ürün Tipi", OFFER_CONSTANTS["Product_Types"])
                st.markdown("---")
                st.write("**Varsayılan Kalite Parametreleri**")
                cols = st.columns(4)
                spec_vals = {}
                keys = list(DEFAULT_QUALITY_PARAMS.keys())
                for i, k in enumerate(keys):
                    col = cols[i % 4]
                    default_val = DEFAULT_QUALITY_PARAMS[k]
                    if isinstance(default_val, (int, float)):
                        spec_vals[k] = col.number_input(k, value=float(default_val))
                    else:
                        spec_vals[k] = col.text_input(k, value=str(default_val))
                
                st.markdown("---")
                if st.form_submit_button("💾 Spesifikasyonu Kaydet"):
                    if spec_name:
                        existing = supabase.table("product_specs").select("id").eq("spec_name", spec_name).execute()
                        if existing.data:
                            st.error("Bu isimde bir spesifikasyon zaten var. Değişiklikleri 'Spesifikasyon Listesi' sekmesinden yapmalısınız.")
                        else:
                            final_params = spec_vals.copy()
                            final_params.update(st.session_state.temp_custom_params)
                            payload = {"spec_name": spec_name, "product_type": prod_type, "parameters": final_params, "created_by": st.session_state.user['email']}
                            try:
                                insert_record("product_specs", payload)
                                st.success("Spesifikasyon Kaydedildi!")
                                st.session_state.temp_custom_params = {}
                            except Exception as e:
                                st.error(f"Hata: {e}")
                    else:
                        st.error("Spesifikasyon Adı gereklidir.")

        with tab_list:
            st.markdown("### Mevcut Spesifikasyonlar")
            specs = get_product_specs()
            if specs:
                df_specs = pd.DataFrame(specs)
                st.dataframe(df_specs[["spec_name", "product_type", "created_by", "created_at"]], use_container_width=True)
                
                st.markdown("---")
                st.markdown("### ✏️ Spesifikasyonu Güncelle")
                
                selected_spec_name_update = st.selectbox("Güncellenecek Spesifikasyonu Seç", ["(Seçiniz)"] + df_specs["spec_name"].tolist())
                
                if selected_spec_name_update != "(Seçiniz)":
                    target_spec = next(s for s in specs if s["spec_name"] == selected_spec_name_update)
                    current_params = target_spec["parameters"]
                    st.info(f"Güncelleniyor: **{target_spec['spec_name']}**")
                    
                    with st.expander("Bu Spesifikasyona Yeni Parametre Ekle"):
                        uc1, uc2 = st.columns(2)
                        up_name = uc1.text_input("Yeni Parametre Adı")
                        up_val = uc2.text_input("Yeni Parametre Değeri")
                        if st.button("Forma Ekle"):
                            if up_name:
                                current_params[up_name] = up_val
                                st.rerun()

                    with st.form("update_spec_form"):
                        u_cols = st.columns(4)
                        updated_vals = {}
                        u_keys = list(current_params.keys())
                        for i, k in enumerate(u_keys):
                            col = u_cols[i % 4]
                            val = current_params[k]
                            if isinstance(val, (int, float)):
                                updated_vals[k] = col.number_input(k, value=float(val))
                            elif isinstance(val, str) and val.replace('.','',1).isdigit():
                                try: updated_vals[k] = col.number_input(k, value=float(val))
                                except: updated_vals[k] = col.text_input(k, value=val)
                            else:
                                updated_vals[k] = col.text_input(k, value=str(val))
                        
                        st.markdown("---")
                        if st.form_submit_button("💾 Spesifikasyonu Güncelle"):
                            try:
                                supabase.table("product_specs").update({"parameters": updated_vals}).eq("id", target_spec['id']).execute()
                                st.success("Spesifikasyon Başarıyla Güncellendi!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Güncelleme Hatası: {e}")
            else:
                st.info("Henüz tanımlı spesifikasyon yok.")
