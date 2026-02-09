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
# Main Modules
MODULE_MAP = {
    1: "1. Satın Alma ve Giriş İşlemleri",
    3: "2. Üretim - Kırma",            
    5: "3. Stok Takibi",               
    7: "4. Kalite Kontrol",
    4: "5. Administrator Settings",    
    6: "6. Offers"                     
}

# Sub-permissions (Tabs)
# Format: Parent_ID: {Sub_ID: "Tab Name"}
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
        portal_tabs = ["Inshell Hazelnuts and Market Updates"]
        if role == 'administrator': portal_tabs.append("Avella Market Price Input (Admin)")
        tabs = st.tabs(portal_tabs)
        with tabs[0]:
            st.header("🌰 Market Updates & Inshell Prices")
            df_prices = get_market_prices()
            if not df_prices.empty:
                st.line_chart(df_prices.set_index('date')[['price_tombul', 'price_cakildak', 'price_levant']])
            else: st.info("No data.")
        if len(tabs) > 1:
            with tabs[1]:
                st.write("Admin Input Placeholder")

    # ==========================
    # MODULE 1: COMBINED
    # ==========================
    elif module == MODULE_MAP[1]:
        st.title("1. Satın Alma ve Giriş İşlemleri")
        
        # PERMISSION CHECK FOR TABS
        tabs_to_show = []
        if has_access(11): tabs_to_show.append("🏪 Şube Alım (Branch)")
        if has_access(12): tabs_to_show.append("🏭 Fabrika Alım (Factory)")
        
        if not tabs_to_show:
            st.error("You have access to this module but no specific tabs.")
        else:
            tabs = st.tabs(tabs_to_show)
            
            # LOGIC FOR TAB 1: SUBE
            if "🏪 Şube Alım (Branch)" in tabs_to_show:
                idx = tabs_to_show.index("🏪 Şube Alım (Branch)")
                with tabs[idx]:
                    st.subheader("Şube Fındık Girişi")
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

            # LOGIC FOR TAB 2: FABRIKA
            if "🏭 Fabrika Alım (Factory)" in tabs_to_show:
                idx = tabs_to_show.index("🏭 Fabrika Alım (Factory)")
                with tabs[idx]:
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

    # ==========================
    # MODULE 3
    # ==========================
    elif module == MODULE_MAP[3]:
        st.title("Modül 3: Üretim - Kırma")
        st.info("Production Module Content")

    # ==========================
    # MODULE 4: ADMIN
    # ==========================
    elif module == MODULE_MAP[4]:
        st.title("🛠️ Administrator Settings")
        
        # PERMISSION CHECK FOR ADMIN TABS
        admin_tabs = []
        if has_access(41): admin_tabs.append("👥 User Permissions")
        if has_access(42): admin_tabs.append("📦 Material Definitions")
        if has_access(43): admin_tabs.append("📜 Login Logs")
        
        if not admin_tabs:
             st.warning("No tabs available.")
        else:
            tabs = st.tabs(admin_tabs)
            
            # USER PERMISSIONS TAB
            if "👥 User Permissions" in admin_tabs:
                with tabs[admin_tabs.index("👥 User Permissions")]:
                    st.subheader("User Permissions")
                    
                    with st.expander("➕ Create User"):
                        with st.form("new_user"):
                            email = st.text_input("Email")
                            pwd = st.text_input("Password", type="password")
                            role_sel = st.selectbox("Role", ["employee", "administrator"])
                            
                            st.write("Permissions:")
                            # DYNAMIC CHECKBOX TREE
                            c1, c2 = st.columns(2)
                            new_mods = []
                            
                            # MOD 1
                            with c1:
                                st.markdown("**1. Purchasing**")
                                if st.checkbox("Mod 1 Access", key="c_m1"): new_mods.append(1)
                                if st.checkbox("  └ Tab: Sube", key="c_m1_11"): new_mods.append(11)
                                if st.checkbox("  └ Tab: Factory", key="c_m1_12"): new_mods.append(12)
                            
                            # MOD 4
                            with c2:
                                st.markdown("**4. Admin**")
                                if st.checkbox("Mod 4 Access", key="c_m4"): new_mods.append(4)
                                if st.checkbox("  └ Tab: Users", key="c_m4_41"): new_mods.append(41)
                                if st.checkbox("  └ Tab: Materials", key="c_m4_42"): new_mods.append(42)
                                if st.checkbox("  └ Tab: Logs", key="c_m4_43"): new_mods.append(43)
                            
                            # For simple modules, just main access
                            with c1:
                                if st.checkbox("3. Production", key="c_m3"): new_mods.append(3)
                                if st.checkbox("5. Stock", key="c_m5"): new_mods.append(5)
                                if st.checkbox("6. Offers", key="c_m6"): new_mods.append(6)
                            
                            with c2:
                                st.markdown("**7. Quality**")
                                if st.checkbox("Mod 7 Access", key="c_m7"): new_mods.append(7)
                                if st.checkbox("  └ Tab: Create", key="c_m7_71"): new_mods.append(71)
                                if st.checkbox("  └ Tab: List", key="c_m7_72"): new_mods.append(72)
                            
                            if st.form_submit_button("Create"):
                                success, msg = register_user(email, pwd, role=role_sel)
                                if success:
                                    # Fetch ID and update
                                    time.sleep(1)
                                    new_user_data = supabase.table("users").select("id").eq("email", email).execute()
                                    if new_user_data.data:
                                        uid = new_user_data.data[0]['id']
                                        update_user_permissions(uid, True, new_mods, role_sel)
                                        st.success("User Created")
                                        time.sleep(1)
                                        st.rerun()
                                else: st.error(msg)
                    
                    st.markdown("---")
                    # EDIT EXISTING
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
                                
                                cur = target.get('allowed_modules', [])
                                if cur is None: cur = []
                                
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
                                    st.success("Updated")
                                    time.sleep(1)
                                    st.rerun()

            # MATERIALS TAB
            if "📦 Material Definitions" in admin_tabs:
                 with tabs[admin_tabs.index("📦 Material Definitions")]:
                     st.write("Material Logic Here (Same as before)")

            # LOGS TAB
            if "📜 Login Logs" in admin_tabs:
                 with tabs[admin_tabs.index("📜 Login Logs")]:
                     st.write("Logs Logic Here (Same as before)")

    # ==========================
    # MODULE 5
    # ==========================
    elif module == MODULE_MAP[5]:
        st.title("📦 Stok Takibi")
        st.info("Stock Content")

    # ==========================
    # MODULE 6
    # ==========================
    elif module == MODULE_MAP[6]:
        st.title("📄 Offers")
        st.info("Offers Content")

    # ==========================
    # MODULE 7
    # ==========================
    elif module == MODULE_MAP[7]:
        st.title("🛡️ Kalite Kontrol")
        
        q_tabs = []
        if has_access(71): q_tabs.append("➕ Create Spec")
        if has_access(72): q_tabs.append("📜 List/Update")
        
        if q_tabs:
            tabs = st.tabs(q_tabs)
            if "➕ Create Spec" in q_tabs:
                with tabs[q_tabs.index("➕ Create Spec")]:
                    st.write("Create Spec Form...")
