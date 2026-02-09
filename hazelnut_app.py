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
if 'active_module' not in st.session_state: st.session_state.active_module = "🌍 Avella Customer Portal"
if 'offer_step' not in st.session_state: st.session_state.offer_step = "menu"
if 'offer_quality_data' not in st.session_state: st.session_state.offer_quality_data = {} 
if 'active_quality_row' not in st.session_state: st.session_state.active_quality_row = None
if 'generated_excel_data' not in st.session_state: st.session_state.generated_excel_data = None
if 'temp_custom_params' not in st.session_state: st.session_state.temp_custom_params = {}

# --- CONSTANTS & PERMISSIONS ---
MODULE_MAP = {
    1: "1. Satın Alma ve Giriş İşlemleri",
    3: "2. Üretim - Kırma",            
    5: "3. Stok Takibi",               
    7: "4. Kalite Kontrol",
    4: "5. Administrator Settings",    
    6: "6. Offers"                     
}

TAB_PERMISSIONS = {
    1: {11: "🏪 Şube Alım (Branch)", 12: "🏭 Fabrika Alım (Factory)"},
    4: {41: "👥 User Permissions", 42: "📦 Material Definitions", 43: "📜 Login Logs"},
    7: {71: "➕ Yeni Spesifikasyon", 72: "📜 Listele/Güncelle"}
}

CUSTOMER_PORTAL_NAME = "🌍 Avella Customer Portal"

# --- HELPER DATA ---
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

CALIBRE_OPTIONS = ["Mixed Size", "21mm+", "20mm+", "19mm+", "18mm+", "17mm+", "16mm+", "15-16mm", "14-15mm", "13-15mm", "13-14mm", "12-14mm", "12-13mm", "11-13mm", "11-12mm", "10-12mm", "10-11mm", "9-11mm", "9-10mm", "9mm-", "9mm+", "0-2mm", "1-3mm", "2-4mm", "4-6mm", "5-7mm", "6-8mm", "7-11mm", "3-11mm", "5-11mm", "15μ", "18μ", "20μ", "21μ", "22μ", "23μ", "24μ", "25μ", "26μ", "27μ", "28μ", "29μ", "30μ", "31μ", "32μ", "33μ", "34μ", "35μ"]

DEFAULT_QUALITY_PARAMS = {"Target Humidity %": "", "Maximum FFA %": 1, "Maximum Peroxide": 1, "Maximum Oversize %": 5, "Maximum Undersize %": 5, "Maximum Visible Rotten %": 2, "Maximum Hidden Rotten %": 2.5, "Maximum Visible Mouldy %": 0.5, "Maximum Hidden Mouldy %": 0.5, "Maximum Visible Tumorous %": 5, "Maximum Hidden Tumorous %": 5, "Maximum Insect Damaged %": 0, "Maximum Twin Kernels %": 2, "Maximum Mech. Damaged %": 8, "Maximum Broken %": 4, "Maximum Rancid %": 1, "Maximum Shrivelled %": 2.5, "Maximum Other Types %": 10, "Maximum Shell Pieces": "0.01%", "Maximum Foreign Matter": 0}

# --- FUNCTIONS ---
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

def get_export_figures():
    try:
        response = supabase.table("export_figures").select("*").order("week_ending_date", desc=False).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['week_ending_date'] = pd.to_datetime(df['week_ending_date'])
            # Calc Avg Price: USD / (Tons * 1000)
            df['avg_kg_price'] = df.apply(lambda x: x['total_export_value_usd'] / (x['total_metric_tons'] * 1000) if x['total_metric_tons'] > 0 else 0, axis=1)
            df['price_change'] = df['avg_kg_price'].diff()
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
    except: pass

def get_product_specs():
    try: return supabase.table("product_specs").select("*").execute().data
    except: return []

def generate_offer_excel(header_data=None, product_df=None, quality_override=None):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    workbook = writer.book
    worksheet = workbook.add_worksheet('Offer Sheet')
    worksheet.set_tab_color('#107C41')

    header_format = workbook.add_format({'bold': True, 'font_size': 14, 'color': '#203764'})
    label_format = workbook.add_format({'bold': True, 'align': 'right', 'bg_color': '#f2f2f2', 'border': 1})
    input_format = workbook.add_format({'border': 1, 'bg_color': '#ffffff'})
    table_header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1, 'text_wrap': True})
    linked_cell_format = workbook.add_format({'bg_color': '#E7E6E6', 'border': 1, 'italic': True, 'font_color': '#595959'})
    quality_header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#FFC000', 'font_color': 'black', 'border': 1, 'text_wrap': True})

    worksheet.write('A1', 'AVELLA OFFER SHEET', header_format)
    headers = [("Date:", "B3", header_data.get("date", "")), ("Offer No:", "D3", header_data.get("offer_no", "")), ("Validity:", "F3", header_data.get("validity", "")), ("Customer Name:", "B4", header_data.get("customer", "")), ("Cust. Ref:", "D4", header_data.get("cust_ref", "")), ("Avella Ref:", "F4", header_data.get("avella_ref", "")), ("Payment Terms:", "B5", header_data.get("payment", "")), ("Delivery Addr:", "D5", header_data.get("delivery", ""))]
    for label, cell, val in headers:
        worksheet.write(cell, label, label_format); col_letter = cell[0]; row_num = int(cell[1:]); input_cell = chr(ord(col_letter) + 1) + str(row_num); worksheet.write(input_cell, str(val), input_format)
    worksheet.merge_range('E5:G5', "", input_format)

    table_start_row = 8
    columns = ["Category", "Product Group", "Total Contract Volume (kg)", "Type/Process", "Variety", "Size", "Packaging", "Net Wgt (kg)", "Price", "Currency", "Incoterms", "Place of Delivery", "Minimum Order Quantity (kg)", "Shipment Schedule", "Payment Terms"]
    for i, col_name in enumerate(columns): worksheet.write(table_start_row, i, col_name, table_header_format); worksheet.set_column(i, i, 15)
    
    worksheet.set_column('B:B', 20); worksheet.set_column('C:C', 20); worksheet.set_column('D:D', 25); worksheet.set_column('E:E', 20); worksheet.set_column('G:G', 25); worksheet.set_column('L:L', 20); worksheet.set_column('M:M', 25); worksheet.set_column('N:N', 20); worksheet.set_column('O:O', 20)

    if product_df is not None and not product_df.empty:
        for idx, row in product_df.iterrows():
            row_num = table_start_row + 1 + idx
            for col_idx, col_name in enumerate(columns):
                val = row.get(col_name, "")
                worksheet.write(row_num, col_idx, val, input_format)

    worksheet_qual = workbook.add_worksheet('Quality Parameters'); worksheet_qual.set_tab_color('#FFC000')
    qual_ident_cols = ["Product Group (Linked)", "Type (Linked)", "Variety (Linked)", "Size (Linked)"]
    used_params = set(DEFAULT_QUALITY_PARAMS.keys())
    param_row_limit = 100
    if product_df is not None:
        param_row_limit = max(100, len(product_df) + 5)
        if quality_override:
            for ridx, params in quality_override.items(): used_params.update(params.keys())
    
    sorted_params = sorted(list(used_params))
    all_qual_cols = qual_ident_cols + sorted_params

    for i, col_name in enumerate(all_qual_cols): worksheet_qual.write(table_start_row, i, col_name, quality_header_format); worksheet_qual.set_column(i, i, 22) 

    for r_idx in range(param_row_limit):
        xl_row = table_start_row + 1 + r_idx + 1
        worksheet_row = table_start_row + 1 + r_idx
        worksheet_qual.write_formula(worksheet_row, 0, f"='Offer Sheet'!B{xl_row}", linked_cell_format) 
        worksheet_qual.write_formula(worksheet_row, 1, f"='Offer Sheet'!D{xl_row}", linked_cell_format) 
        worksheet_qual.write_formula(worksheet_row, 2, f"='Offer Sheet'!E{xl_row}", linked_cell_format) 
        worksheet_qual.write_formula(worksheet_row, 3, f"='Offer Sheet'!F{xl_row}", linked_cell_format) 
        row_custom_data = {}
        if quality_override and r_idx in quality_override: row_custom_data = quality_override[r_idx]
        for i, key in enumerate(sorted_params):
            val = row_custom_data.get(key, DEFAULT_QUALITY_PARAMS.get(key, ""))
            worksheet_qual.write(worksheet_row, 4 + i, val, input_format)

    ref_sheet = workbook.add_worksheet('ReferenceData'); ref_sheet.hide()
    def write_list_to_ref(header, data_list, col_idx):
        ref_sheet.write(0, col_idx, header); [ref_sheet.write(i + 1, col_idx, item) for i, item in enumerate(data_list)]; return f"=ReferenceData!${xlsxwriter.utility.xl_col_to_name(col_idx)}$2:${xlsxwriter.utility.xl_col_to_name(col_idx)}${len(data_list) + 1}"
    
    cat_range = write_list_to_ref("Categories", OFFER_CONSTANTS["Categories"], 0); group_range = write_list_to_ref("Groups", OFFER_CONSTANTS["Product_Groups"], 1); type_range = write_list_to_ref("Types", OFFER_CONSTANTS["Product_Types"], 2); var_range = write_list_to_ref("Varieties", OFFER_CONSTANTS["Varieties"], 3); size_range = write_list_to_ref("Sizes", OFFER_CONSTANTS["Sizes"], 4); pack_range = write_list_to_ref("Packaging", OFFER_CONSTANTS["Packaging"], 5); curr_range = write_list_to_ref("Currencies", OFFER_CONSTANTS["Currencies"], 6); inco_range = write_list_to_ref("Incoterms", OFFER_CONSTANTS["Incoterms"], 7)
    
    val_end = table_start_row + 1 + 100
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
# 🔐 AUTHENTICATION
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
# 🚀 MAIN APP - MULTI-MENU SIDEBAR
# ==========================================
else:
    user = st.session_state.user; role = st.session_state.role
    st.sidebar.info(f"👤 {user['email']}"); st.sidebar.caption(f"Rol: {role.upper()}")
    if st.sidebar.button("Çıkış Yap"): st.session_state.user = None; st.session_state.role = None; st.rerun()

    # --- PERMISSIONS ---
    def has_access(mod_id):
        if role == 'administrator': return True
        return mod_id in user.get('allowed_modules', [])

    # --- MENU LISTS ---
    menu_tr = []; menu_mgmt = []; menu_prt = []
    
    if has_access(1): menu_tr.append(MODULE_MAP[1])
    if has_access(3): menu_tr.append(MODULE_MAP[3])
    if has_access(5): menu_tr.append(MODULE_MAP[5])
    if has_access(7): menu_tr.append(MODULE_MAP[7])
    
    if has_access(4): menu_mgmt.append(MODULE_MAP[4])
    if has_access(6): menu_mgmt.append(MODULE_MAP[6])
    
    menu_prt.append(CUSTOMER_PORTAL_NAME)

    st.sidebar.markdown("---")
    
    # SECTION 1: TURKIYE
    if menu_tr:
        with st.sidebar.expander("🇹🇷 Avella Turkiye", expanded=True):
            val_tr = st.radio("Select Module", menu_tr, key="radio_tr", label_visibility="collapsed")
            if st.button("Modüle gidiniz"):
                st.session_state.active_module = val_tr
                st.rerun()

    if menu_mgmt:
        st.sidebar.markdown("---")
        with st.sidebar.expander("🏢 Avella Management", expanded=True):
            val_mgmt = st.radio("Select Module", menu_mgmt, key="radio_mgmt", label_visibility="collapsed")
            if st.button("Go to the Module"):
                st.session_state.active_module = val_mgmt
                st.rerun()

    st.sidebar.markdown("---")
    with st.sidebar.expander("🤝 Customers & Partners", expanded=True):
        val_prt = st.radio("Select Module", menu_prt, key="radio_prt", label_visibility="collapsed")
        if st.button("Go to Portal"):
            st.session_state.active_module = val_prt
            st.rerun()

    module = st.session_state.active_module

    # ==========================
    # CUSTOMER PORTAL
    # ==========================
    if module == CUSTOMER_PORTAL_NAME:
        st.title(CUSTOMER_PORTAL_NAME)
        portal_tabs = ["Inshell Hazelnuts and Market Updates", "Weekly Export Figures"]
        if role == 'administrator': 
            portal_tabs.append("Admin: Input Export Figures")
            portal_tabs.append("Admin: Input Inshell Market Price")
        
        tabs = st.tabs(portal_tabs)
        
        # TAB 1: INSHELL
        with tabs[0]:
            st.header("🌰 Market Updates & Inshell Prices")
            df_prices = get_market_prices()
            live_rates = get_live_rates()
            with st.expander("Live Currency Rates (Auto-fetched)", expanded=True):
                c1, c2 = st.columns(2)
                c1.metric("USD/TRY", f"{live_rates.get('USD', 0):.4f}")
                c2.metric("EUR/TRY", f"{live_rates.get('EUR', 0):.4f}")
            
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
                    fig.update_layout(title=dict(text=title), xaxis=dict(title="Date", rangeslider=dict(visible=True), type="date", range=[start_window, max_db_date]), yaxis=dict(title=dict(text=y_label, font=dict(color="black"))), hovermode="x unified", height=500)
                    return fig
                st.plotly_chart(build_chart("1. Inshell Prices (TL/kg)", 'TL', "Price (TL)"), use_container_width=True)
                st.plotly_chart(build_chart("2. Inshell Prices (USD/kg)", 'USD', "Price (USD)"), use_container_width=True)
                st.plotly_chart(build_chart("3. Inshell Prices (EUR/kg)", 'EUR', "Price (EUR)"), use_container_width=True)
            else: st.info("No market price data available yet.")

        # TAB 2: EXPORT
        with tabs[1]:
            st.header("🚢 Weekly Export Figures from Turkey")
            df_export = get_export_figures()
            if not df_export.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_export['week_ending_date'], y=df_export['total_metric_tons'], name="Metric Tons", yaxis="y1", line=dict(color='blue', width=3)))
                fig.add_trace(go.Scatter(x=df_export['week_ending_date'], y=df_export['total_export_value_usd'], name="Total Value ($)", yaxis="y2", line=dict(color='green', width=3)))
                fig.add_trace(go.Scatter(x=df_export['week_ending_date'], y=df_export['avg_kg_price'], name="Avg KG Price ($)", yaxis="y3", line=dict(color='red', width=3, dash='dot')))
                fig.update_layout(
                    title=dict(text="Weekly Export Correlations"), 
                    xaxis=dict(domain=[0.05, 0.9], rangeslider=dict(visible=True), type="date"),
                    yaxis=dict(title=dict(text="Metric Tons", font=dict(color="blue")), tickfont=dict(color="blue"), dtick=500), 
                    yaxis2=dict(title=dict(text="Total Value ($)", font=dict(color="green")), tickfont=dict(color="green"), anchor="x", overlaying="y", side="right", dtick=5000000), 
                    yaxis3=dict(title=dict(text="Avg Price ($/kg)", font=dict(color="red")), tickfont=dict(color="red"), anchor="free", overlaying="y", side="right", position=0.95, range=[5, 20]), 
                    # --- LEGEND MOVED TO BOTTOM ---
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.3, # Moves legend below X-axis
                        xanchor="center",
                        x=0.5
                    ),
                    height=600
                )
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("No export data available.")

        # ADMIN TABS
        if role == 'administrator' and len(tabs) > 2:
            with tabs[2]:
                st.header("📝 Input Export Figures")
                with st.form("export_input"):
                    c1, c2, c3 = st.columns(3)
                    date_in = c1.date_input("Week Ending Date", value=datetime.now())
                    tons_in = c2.number_input("Total Metric Tons", min_value=0.0, step=100.0)
                    val_in = c3.number_input("Total Export Value (USD)", min_value=0.0, step=100000.0)
                    if st.form_submit_button("Save Weekly Figure"):
                        if tons_in > 0 and val_in > 0:
                            try:
                                supabase.table("export_figures").upsert({"week_ending_date": str(date_in), "total_metric_tons": tons_in, "total_export_value_usd": val_in, "created_by": st.session_state.user['email']}, on_conflict="week_ending_date").execute()
                                st.success("Saved!"); time.sleep(1); st.rerun()
                            except Exception as e: st.error(f"Error: {e}")
                        else: st.warning("Please enter valid Tons and Value.")
                st.markdown("### 📊 Data Table")
                df_ex = get_export_figures()
                if not df_ex.empty:
                    st.dataframe(df_ex[['week_ending_date', 'total_metric_tons', 'total_export_value_usd', 'avg_kg_price', 'price_change']].sort_values('week_ending_date', ascending=False).style.format({"total_metric_tons": "{:,.2f}", "total_export_value_usd": "${:,.2f}", "avg_kg_price": "${:.2f}", "price_change": "{:+.2f}"}), use_container_width=True)
            
            with tabs[3]:
                st.header("📝 Input Daily Market Prices")
                live_rates = get_live_rates()
                with st.form("price_input_form"):
                    d_date = st.date_input("Date", value=datetime.now()); st.caption("Enter prices for ALL 3 types (TL/kg)."); c1, c2, c3 = st.columns(3); p_tombul = c1.number_input("Tombul", min_value=0.0, step=0.5); p_cakildak = c2.number_input("Cakildak", min_value=0.0, step=0.5); p_levant = c3.number_input("Levant", min_value=0.0, step=0.5)
                    st.markdown("---"); st.write("**Exchange Rates (Auto-fetched)**"); c4, c5 = st.columns(2); r_usd = c4.number_input("USD/TRY Rate", min_value=0.0, step=0.01, format="%.4f", value=live_rates.get("USD", 34.50)); r_eur = c5.number_input("EUR/TRY Rate", min_value=0.0, step=0.01, format="%.4f", value=live_rates.get("EUR", 37.20))
                    if st.form_submit_button("Save Entry"):
                        if p_tombul > 0:
                            payload = {"date": str(d_date), "price_tombul": p_tombul, "price_cakildak": p_cakildak, "price_levant": p_levant, "rate_usd_try": r_usd, "rate_eur_try": r_eur, "created_by": st.session_state.user['email']}
                            try: supabase.table("market_prices").upsert(payload, on_conflict="date").execute(); st.success("Saved!"); time.sleep(1); st.rerun()
                            except Exception as e: st.error(f"Error: {e}")
                
                # RESTORED HISTORICAL DATA TABLE
                st.markdown("### 📜 Historical Data Input")
                df_hist = get_market_prices()
                if not df_hist.empty:
                    disp_cols = ["id", "date", "price_tombul", "price_cakildak", "price_levant", "rate_usd_try", "rate_eur_try", "created_by"]
                    valid_cols = [c for c in disp_cols if c in df_hist.columns]
                    st.dataframe(df_hist[valid_cols].sort_values(by='date', ascending=False).style.format({"price_tombul": "{:.2f}", "price_cakildak": "{:.2f}", "price_levant": "{:.2f}", "rate_usd_try": "{:.4f}", "rate_eur_try": "{:.4f}"}), use_container_width=True, hide_index=True)

    # ==========================
    # MODULE 1: COMBINED
    # ==========================
    elif module == MODULE_MAP[1]:
        st.title("1. Satın Alma ve Giriş İşlemleri")
        
        tabs_to_show = []
        if has_access(11): tabs_to_show.append("🏪 Şube Alım (Branch)")
        if has_access(12): tabs_to_show.append("🏭 Fabrika Alım (Factory)")
        
        if not tabs_to_show: st.error("You have access to this module but no specific tabs.")
        else:
            tabs = st.tabs(tabs_to_show)
            if "🏪 Şube Alım (Branch)" in tabs_to_show:
                with tabs[tabs_to_show.index("🏪 Şube Alım (Branch)")]:
                    st.subheader("Şube Fındık Girişi")
                    with st.form("sube_hazelnut_form"):
                        st.subheader("1. Müstahsil & Tedarikçi"); c1, c2, c3 = st.columns(3); supplier = c1.text_input("Tedarikçi Adı"); sup_type = c2.selectbox("Tedarikçi Tipi", ["Müstahsil", "Tüccar", "Şirket"]); id_num = c3.text_input("TCKN / VKN"); c4, c5, c6 = st.columns(3); city = c4.text_input("İl"); dist_in = c5.text_input("İlçe"); vill_in = c6.text_input("Köy / Mahalle"); c_cont, c_cert = st.columns(2); contact = c_cont.text_input("Telefon No"); cert_status = c_cert.selectbox("Sertifikasyon", ["Yok", "Organik", "Rainforest Alliance", "Avella"]); st.markdown("---"); c7, c8, c9 = st.columns(3); reg_type = c7.selectbox("Alım Şekli", ["Satın Alma", "Emanet"]); location = c8.selectbox("Teslimat Yeri", ["Fabrika", "Tarla", "Avella Şube"]); hazelnut_type = c9.selectbox("Fındık Çeşidi", ["Karışık", "Giresun Tombul", "Çakıldak", "Kara", "Sivri", "Palaz", "Badem", "Foşa", "Yomra"]); st.markdown("---"); price_gross=0.0; price_net_deducted=0.0; val_randiman=0.0; st.subheader("2. Kalite, Miktar ve Fiyatlandırma"); col_q1, col_q2 = st.columns([1, 1])
                        with col_q1: st.markdown("**Fiziksel Analiz (Eksper)**"); w_sample = st.number_input("Kabuklu Numune Ağırlığı (g)", value=250.0); w_good = st.number_input("Sağlam İç (g)", 0.0); w_shriv = st.number_input("Buruşuk İç (g)", 0.0); w_vis_rot = st.number_input("Görünen Çürük (g)", 0.0); w_hid_rot = st.number_input("Gizli Çürük (g)", 0.0); w_tumor = st.number_input("Ur (g)", 0.0); s1, s2 = st.columns(2); w_over = s1.number_input("1. Numara İç - 13 mm üzeri (g)", 0.0); w_under = s2.number_input("Elek Altı İç - 9 mm altı (g)", 0.0); val_moist = st.number_input("Nem (%)", 0.0, 100.0, 5.0)
                        with col_q2: st.markdown("**Miktar ve Fiyatlandırma**"); net_weight = st.number_input("Toplam Net Ağırlık (kg)", min_value=0.0); st.caption("Paket Adetleri"); p1, p2, p3 = st.columns(3); cnt_nylon = p1.number_input("Naylon", min_value=0); cnt_jute = p2.number_input("Jüt", min_value=0); cnt_bigbag = p3.number_input("Big Bag", min_value=0)
                        if reg_type == "Emanet": st.info("Emanet Alım: Fiyat 0 TL"); price_gross = 0.0
                        else: price_gross = st.number_input("Borsa Fiyatı (50 Randıman)", value=120.0)
                        st.markdown("---"); calc_pressed = st.form_submit_button("🔄 Randıman ve Fiyat Hesapla"); val_randiman = calculate_randiman(w_sample, w_good, w_shriv); net_price_50 = price_gross / 1.0245; unit_price = net_price_50 * (val_randiman / 50.0); total_val = unit_price * net_weight
                        if calc_pressed: st.markdown("##### Analiz Sonuçları"); st.metric("Randıman", f"%{val_randiman:.2f}"); 
                        if reg_type != "Emanet": st.success(f"💰 **TOPLAM TUTAR:** {total_val:,.2f} TL")
                        st.markdown("---"); st.subheader("3. Ödeme ve Kayıt"); f1, f2, f3 = st.columns(3); doc_num = f1.text_input("Makbuz / Fatura No"); pay_amount = f2.number_input("Ödenen Tutar", 0.0); pay_method = f3.selectbox("Ödeme Yöntemi", ["Nakit", "Banka", "Çek"]); 
                        if reg_type != "Emanet": st.metric("Kalan Bakiye", f"{total_val - pay_amount:,.2f} TL")
                        if st.form_submit_button("✅ Şube Girişini Kaydet"):
                            payload = {"created_by": st.session_state.user['email'], "status": "Pending Arrival", "category": hazelnut_cat, "supplier": supplier, "supplier_type": sup_type, "id_number": id_num, "city": city, "district": dist_in, "village": vill_in, "phone_number": contact, "cert_status": cert_status, "reg_type": reg_type, "location": location, "item_type": hazelnut_type, "qty_ordered": net_weight, "total_value": total_val, "document_number": doc_num, "payment_amount": pay_amount, "remaining_balance": total_val - pay_amount, "count_nylon": cnt_nylon, "count_jute": cnt_jute, "count_bigbag": cnt_bigbag, "weight_sample": w_sample, "weight_good": w_good, "weight_shrivelled": w_shriv, "weight_visible_rotten": w_vis_rot, "weight_hidden_rotten": w_hid_rot, "weight_tumor": w_tumor, "weight_undersize": w_under, "weight_oversize": w_over, "moisture": val_moist, "calculated_randiman": val_randiman, "gross_price_50": price_gross, "net_price_50": net_price_50, "actual_unit_price": unit_price}; insert_record("purchases", payload); st.success("Şube Girişi Kaydedildi!")

            if "🏭 Fabrika Alım (Factory)" in tabs_to_show:
                with tabs[tabs_to_show.index("🏭 Fabrika Alım (Factory)")]:
                    st.subheader("Fabrika Alım Operasyonları")
                    f_tab1, f_tab2, f_tab3 = st.tabs(["🌰 Fındık Alımı", "📦 Malzeme Alımı", "⚙️ Makine & Hizmet"])
                    with f_tab1:
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
                    
                    with f_tab2:
                        st.subheader("Malzeme Seçimi"); material_cats = ["Ambalaj Malzemeleri", "Bakım Malzemeleri", "Ofis Malzemeleri", "Temizlik Malzemeleri", "Eşantiyon & Hediye", "İş Kıyafetleri", "Gıda ve Mutfak", "Diğer"]; c_cat, c_item = st.columns(2); selected_mat_cat = c_cat.selectbox("Kategori", material_cats, key="mat_cat_fab"); 
                        try: response = supabase.table("material_definitions").select("*").eq("category", selected_mat_cat).execute(); items_data = response.data; item_names = [row['item_name'] for row in items_data]
                        except: items_data = []; item_names = []
                        if item_names: selected_item_name = c_item.selectbox("Malzeme Seç", item_names, key="mat_item_fab"); selected_item_data = next((item for item in items_data if item["item_name"] == selected_item_name), None)
                        else: c_item.warning("Tanımlı malzeme yok."); selected_item_name = c_item.text_input("Manuel Giriş", key="mat_manual_fab")
                        with st.form("fab_material_purchase"): 
                            supplier = st.text_input("Tedarikçi"); c3, c4 = st.columns(2); qty = c3.number_input("Miktar", min_value=1.0); price = c4.number_input("Tutar (TL)", min_value=0.0); 
                            if st.form_submit_button("✅ Kaydet"): payload = {"category": "Malzeme", "supplier": supplier, "item_type": selected_item_name, "item_sub_type": selected_mat_cat, "qty_ordered": qty, "total_value": price, "status": "Pending Arrival", "created_by": st.session_state.user['email']}; insert_record("purchases", payload); st.success("Kaydedildi!")
                    
                    with f_tab3:
                        st.subheader("Genel Alım"); general_type = st.selectbox("Tür", ["Makine", "Hizmet"], key="gen_type_fab"); 
                        with st.form("fab_gen_form"): 
                            c1, c2 = st.columns(2); supplier = c1.text_input("Firma"); desc = c2.text_input("Açıklama"); c3, c4 = st.columns(2); qty = c3.number_input("Miktar", 1.0); price = c4.number_input("Tutar", 0.0); 
                            if st.form_submit_button("✅ Kaydet"): insert_record("purchases", {"category": general_type, "supplier": supplier, "item_type": desc, "qty_ordered": qty, "total_value": price, "status": "Pending Arrival", "created_by": st.session_state.user['email']}); st.success("Kaydedildi!")

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
    # MODULE 4: ADMIN
    # ==========================
    elif module == MODULE_MAP[4]:
        st.title("🛠️ Administrator Settings")
        
        admin_tabs = []
        if has_access(41): admin_tabs.append("👥 User Permissions")
        if has_access(42): admin_tabs.append("📦 Material Definitions")
        if has_access(43): admin_tabs.append("📜 Login Logs")
        
        if not admin_tabs: st.warning("No tabs available.")
        else:
            tabs = st.tabs(admin_tabs)
            
            if "👥 User Permissions" in admin_tabs:
                with tabs[admin_tabs.index("👥 User Permissions")]:
                    st.subheader("User Permissions")
                    with st.expander("➕ Create User"):
                        with st.form("new_user"):
                            email = st.text_input("Email")
                            pwd = st.text_input("Password", type="password")
                            role_sel = st.selectbox("Role", ["employee", "administrator"])
                            st.write("Permissions:")
                            c1, c2 = st.columns(2)
                            new_mods = []
                            
                            with c1:
                                st.markdown("**1. Purchasing**")
                                if st.checkbox("Mod 1 Access", key="c_m1"): new_mods.append(1)
                                if st.checkbox("  └ Tab: Sube", key="c_m1_11"): new_mods.append(11)
                                if st.checkbox("  └ Tab: Factory", key="c_m1_12"): new_mods.append(12)
                                if st.checkbox("3. Production", key="c_m3"): new_mods.append(3)
                                if st.checkbox("5. Stock", key="c_m5"): new_mods.append(5)

                            with c2:
                                st.markdown("**4. Admin**")
                                if st.checkbox("Mod 4 Access", key="c_m4"): new_mods.append(4)
                                if st.checkbox("  └ Tab: Users", key="c_m4_41"): new_mods.append(41)
                                if st.checkbox("  └ Tab: Materials", key="c_m4_42"): new_mods.append(42)
                                if st.checkbox("  └ Tab: Logs", key="c_m4_43"): new_mods.append(43)
                                if st.checkbox("6. Offers", key="c_m6"): new_mods.append(6)
                                st.markdown("**7. Quality**")
                                if st.checkbox("Mod 7 Access", key="c_m7"): new_mods.append(7)
                                if st.checkbox("  └ Tab: Create", key="c_m7_71"): new_mods.append(71)
                                if st.checkbox("  └ Tab: List", key="c_m7_72"): new_mods.append(72)
                            
                            if st.form_submit_button("Create"):
                                success, msg = register_user(email, pwd, role=role_sel)
                                if success:
                                    time.sleep(1); new_user_data = supabase.table("users").select("id").eq("email", email).execute()
                                    if new_user_data.data:
                                        uid = new_user_data.data[0]['id']
                                        update_user_permissions(uid, True, new_mods, role_sel)
                                        st.success("User Created"); time.sleep(1); st.rerun()
                                else: st.error(msg)
                    
                    st.markdown("---")
                    all_users = get_all_users()
                    if all_users:
                        user_list = {u['email']: u for u in all_users}
                        sel_u = st.selectbox("Edit User", list(user_list.keys()))
                        if sel_u:
                            target = user_list[sel_u]
                            with st.form("edit_u"):
                                st.write(f"Editing: {target['email']}")
                                new_r = st.selectbox("Role", ["employee", "administrator"], index=["employee", "administrator"].index(target['role']) if target['role'] in ["employee", "administrator"] else 0)
                                new_app = st.checkbox("Approved", target['is_approved'])
                                cur = target.get('allowed_modules', []) or []
                                u_mods = []
                                ec1, ec2 = st.columns(2)
                                
                                with ec1:
                                    st.markdown("**1. Purchasing**")
                                    if st.checkbox("Mod 1 Access", 1 in cur, key="e_m1"): u_mods.append(1)
                                    if st.checkbox("  └ Sube", 11 in cur, key="e_m1_11"): u_mods.append(11)
                                    if st.checkbox("  └ Factory", 12 in cur, key="e_m1_12"): u_mods.append(12)
                                    if st.checkbox("3. Production", 3 in cur, key="e_m3"): u_mods.append(3)
                                    if st.checkbox("5. Stock", 5 in cur, key="e_m5"): u_mods.append(5)
                                
                                with ec2:
                                    st.markdown("**4. Admin**")
                                    if st.checkbox("Mod 4 Access", 4 in cur, key="e_m4"): u_mods.append(4)
                                    if st.checkbox("  └ Users", 41 in cur, key="e_m4_41"): u_mods.append(41)
                                    if st.checkbox("  └ Materials", 42 in cur, key="e_m4_42"): u_mods.append(42)
                                    if st.checkbox("  └ Logs", 43 in cur, key="e_m4_43"): u_mods.append(43)
                                    if st.checkbox("6. Offers", 6 in cur, key="e_m6"): u_mods.append(6)
                                    st.markdown("**7. Quality**")
                                    if st.checkbox("Mod 7 Access", 7 in cur, key="e_m7"): u_mods.append(7)
                                    if st.checkbox("  └ Create", 71 in cur, key="e_m7_71"): u_mods.append(71)
                                    if st.checkbox("  └ List", 72 in cur, key="e_m7_72"): u_mods.append(72)
                                
                                if st.form_submit_button("Update"):
                                    update_user_permissions(target['id'], new_app, u_mods, new_r)
                                    st.success("Updated"); time.sleep(1); st.rerun()

            if "📦 Material Definitions" in admin_tabs:
                with tabs[admin_tabs.index("📦 Material Definitions")]:
                    cats = ["Ambalaj Malzemeleri", "Bakım Malzemeleri", "Ofis Malzemeleri", "Temizlik Malzemeleri", "Eşantiyon & Hediye", "İş Kıyafetleri", "Gıda ve Mutfak", "Diğer"]; units = ['adet', 'gr', 'kg', 'bobin', 'rulo', 'paket', 'deste', 'palet', 'litre', 'mililitre', 'metreküp', 'desimetreküp', 'santimetreküp', 'metre', 'desimetre', 'santimetre', 'milimetre', 'bigbag', 'kamyon', 'tır', 'tank', 'metrekare', 'santimetrekare', 'ar', 'dekar', 'hektar']; 
                    with st.expander("View List"): data = supabase.table("material_definitions").select("*").execute().data; st.dataframe(pd.DataFrame(data), use_container_width=True)
                    st.write("### ➕ Add / ✏️ Edit / 🗑️ Delete"); action = st.radio("Action", ["Add", "Edit", "Delete"], horizontal=True)
                    if action == "Add":
                        with st.form("add_mat"): 
                            c1, c2 = st.columns(2); cat = c1.selectbox("Category", cats); name = c2.text_input("Name"); u1, u2 = st.columns(2); unit = u1.selectbox("Unit", units); uq = u2.number_input("Unit Qty", 1.0); nt = st.text_area("Notes"); 
                            if st.form_submit_button("Save"): insert_record("material_definitions", {"category": cat, "item_name": name, "sales_unit": unit, "unit_quantity": uq, "notes": nt}); st.success("Added!")
                    elif action == "Edit":
                        sel_cat = st.selectbox("Category", cats); items = supabase.table("material_definitions").select("*").eq("category", sel_cat).execute().data
                        if items:
                            target = st.selectbox("Material", [i['item_name'] for i in items]); row = next(i for i in items if i['item_name'] == target); 
                            with st.form("edit_mat"): 
                                new_name = st.text_input("Name", row['item_name']); 
                                if st.form_submit_button("Update"): supabase.table("material_definitions").update({"item_name": new_name}).eq("id", row['id']).execute(); st.success("Updated!")
                    elif action == "Delete":
                        sel_cat = st.selectbox("Category (Delete)", cats); items = supabase.table("material_definitions").select("*").eq("category", sel_cat).execute().data
                        if items:
                            target = st.selectbox("Select", [i['item_name'] for i in items]); 
                            if st.button("Delete"): supabase.table("material_definitions").delete().eq("item_name", target).execute(); st.success("Deleted!")

            if "📜 Login Logs" in admin_tabs:
                with tabs[admin_tabs.index("📜 Login Logs")]:
                    try:
                        logs = supabase.table("login_logs").select("*").order("login_at", desc=True).limit(1000).execute().data
                        if logs: st.dataframe(pd.DataFrame(logs))
                        else: st.info("No logs.")
                    except: st.error("Error loading logs.")

    elif module == MODULE_MAP[5]:
        st.title("📦 Stok Takibi"); moves = supabase.table("stock_movements").select("*").execute().data; df = pd.DataFrame(moves)
        if not df.empty: stock = df.groupby('item_name')['quantity'].sum().reset_index(); st.dataframe(stock, use_container_width=True); st.markdown("---"); st.dataframe(df.sort_values(by='created_at', ascending=False))
        else: st.info("Hareket yok.")

    elif module == MODULE_MAP[6]:
        st.title("📄 Offers")
        
        if st.session_state.offer_step == "menu":
            if st.button("➕ Create New Offer", type="primary"):
                st.session_state.offer_step = "create"; st.rerun()
            st.info("Click above to start a new offer.")

        elif st.session_state.offer_step == "create":
            if st.button("⬅️ Back to Menu"):
                st.session_state.offer_step = "menu"; st.rerun()
            st.markdown("### 📝 Offer Details & Product List")
            with st.container():
                c1, c2, c3 = st.columns(3)
                date_val = c1.date_input("Date", value=datetime.now())
                offer_no = c2.text_input("Offer No")
                validity = c3.text_input("Validity")
                c4, c5, c6 = st.columns(3)
                customer = c4.text_input("Customer Name"); cust_ref = c5.text_input("Cust. Ref"); avella_ref = c6.text_input("Avella Ref")
                c7, c8 = st.columns(2)
                payment = c7.text_input("Payment Terms"); delivery = c8.text_input("Delivery Address")
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
                st.session_state.offer_step = "create"; st.rerun()
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
                    if isinstance(default_val, (int, float)): new_vals[k] = col.number_input(k, value=float(default_val))
                    else: new_vals[k] = col.text_input(k, value=str(default_val))
                st.markdown("---")
                if st.form_submit_button("✅ Save Parameters & Return"):
                    st.session_state.offer_quality_data[row_idx] = new_vals
                    st.session_state.offer_rows.at[row_idx, "Quality Parameters"] = "Updated"
                    st.session_state.offer_step = "create"; st.rerun()

    # ==========================
    # MODULE 7: QUALITY
    # ==========================
    elif module == MODULE_MAP.get(7): 
        st.title("🛡️ Kalite Kontrol & Spesifikasyonlar")
        
        q_tabs = []
        if has_access(71): q_tabs.append("➕ Yeni Spesifikasyon")
        if has_access(72): q_tabs.append("📜 Listele/Güncelle")
        
        if not q_tabs: st.warning("No tabs available.")
        else:
            tabs = st.tabs(q_tabs)
            
            if "➕ Yeni Spesifikasyon" in q_tabs:
                with tabs[q_tabs.index("➕ Yeni Spesifikasyon")]:
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
                            else: st.error("İsim gerekli")
                    
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
                            else: st.error("Spesifikasyon Adı gereklidir.")

            if "📜 Listele/Güncelle" in q_tabs:
                with tabs[q_tabs.index("📜 Listele/Güncelle")]:
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
                                        time.sleep(1); st.rerun()
                                    except Exception as e: st.error(f"Güncelleme Hatası: {e}")
                    else: st.info("Henüz tanımlı spesifikasyon yok.")
