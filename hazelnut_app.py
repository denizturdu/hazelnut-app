import streamlit as st
import pandas as pd
from db_utils import supabase, login_user, register_user, insert_record, get_all_users, update_user_permissions
import time
import io
import xlsxwriter
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Fındık Fabrikası Yönetimi", layout="wide")

# --- SESSION STATE SETUP ---
if 'user' not in st.session_state: st.session_state.user = None
if 'role' not in st.session_state: st.session_state.role = None

# --- CONSTANTS ---
MODULE_MAP = {
    1: "1. Şube Ürün Girişi",
    2: "2. Fabrika Ürün Girişi",
    3: "3. Mal Kabul (Kantar)",
    4: "4. Yönetici Ayarları",
    5: "5. Stok Takibi",
    6: "6. Teklifler (Offers)"
}

CUSTOMER_PORTAL_NAME = "🌍 Avella Customer Portal"

CALIBRE_OPTIONS = [
    "Mixed Size", "21mm+", "20mm+", "19mm+", "18mm+", "17mm+", "16mm+", 
    "15-16mm", "14-15mm", "13-15mm", "13-14mm", "12-14mm", "12-13mm", 
    "11-13mm", "11-12mm", "10-12mm", "10-11mm", "9-11mm", "9-10mm", 
    "9mm-", "9mm+", "0-2mm", "1-3mm", "2-4mm", "4-6mm", "5-7mm", 
    "6-8mm", "7-11mm", "3-11mm", "5-11mm", "15μ", "18μ", "20μ", 
    "21μ", "22μ", "23μ", "24μ", "25μ", "26μ", "27μ", "28μ", "29μ", 
    "30μ", "31μ", "32μ", "33μ", "34μ", "35μ"
]

# --- HELPER FUNCTIONS ---
def calculate_randiman(sample_w, good, shriv):
    if sample_w == 0: return 0.0
    return ((good + (shriv / 2)) / sample_w) * 100

def get_market_prices():
    """Fetch all market prices sorted by date."""
    try:
        response = supabase.table("market_prices").select("*").order("date", desc=False).execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame()

def generate_offer_excel():
    """Generates the Offer Excel file in memory with Linked Quality Sheet and Defaults."""
    output = io.BytesIO()
    
    # 1. Define Master Data
    data = {
        "Categories": ["Nuts", "Dried Fruit", "Oil", "Chocolate"],
        "Product_Groups": [
            "Hazelnuts", "Walnuts", "Pistachios", "Almonds", "Peanuts",
            "Cashew Nuts", "Brazil Nuts", "Pine Nuts", "Macadamia Nuts", "Pecan Nuts",
            "Apricots", "Raisins", "Figs", "Plums",
            "Hazelnut Oil", "Olive Oil",
            "Hazelnut Cream", "Hazelnut Crunch", "Pistachio Cream", "Pistachio Crunch"
        ],
        "Product_Types": [
            "Inshell", "Inshell - Harmanici", "Natural Kernels - Whole",
            "Natural Kernels - Shrivelled", "Natural Kernels - Scratched",
            "Natural Kernels - Broken", "Natural Kernels - Rotten", "Natural Kernels - Mix Reject",
            "Natural and Slivered", "Blanched Kernels - Whole",
            "Blanched and Chopped Pieces", "Blanched and Slivered", "Blanched and Diced",
            "Blanched and Scratched", "Blanched and Broken", "Blanched Flour",
            "Roasted Kernels - Whole", "Roasted and Chopped Pieces", "Roasted and Slivered",
            "Roasted and Diced", "Roasted and Scratched", "Roasted and Broken",
            "Roasted Flour", "Light Paste", "Dark Paste", "Medium Paste", "Shells"
        ],
        "Varieties": [
            "Karışık", "Giresun Tombul", "Çakıldak", "Kara", "Sivri", "Palaz", "Badem", "Foşa", "Yomra",
            "Nonpareil", "Carmel", "Butte", "Padre", "Sonora", "Monterey", "Marcona", "Guara",
            "Kirmizi", "Uzun", "Halebi", "Siirt", "Ohadi", "Fandoghi", "Kalleh Ghouchi",
            "Ahmad Aghaei", "Akbari", "Kerman", "Golden Hills", "Lost Hills", "Kalehghouchi", "Gumdrop",
            "Chandler", "Hartley", "Howard", "Franquette", "Serr", "Tulare", "Pedro",
            "Şebin", "Bilecik", "Yalova", "Kaman", "Kaplan", "Şen", "Tokat"
        ],
        "Sizes": [
            "Mixed Size", "21mm+", "20mm+", "19mm+", "18mm+", "17mm+", "16mm+",
            "14-16mm", "13-15mm", "15-16mm", "14-15mm", "13-14mm", "12-14mm", "12-13mm", 
            "11-13mm", "11-12mm", "10-12mm", "10-11mm", "9-11mm", "9-10mm", "9mm-", "9mm+", 
            "0-2mm", "1-3mm", "2-4mm", "4-6mm", "5-7mm", "6-8mm", "7-11mm", "3-11mm", "5-11mm",
            "15μ", "18μ", "20μ", "21μ", "22μ", "23μ", "24μ", "25μ", "26μ", "27μ", "28μ",
            "29μ", "30μ", "31μ", "32μ", "33μ", "34μ", "35μ",
            "18/20 mm", "20/22 mm", "22/24 mm", "24/26 mm", "26/28 mm", "28/30 mm",
            "30/32 mm", "32/34 mm", "34/36 mm", "36+ mm",
            "18/20 (US)", "20/22 (US)", "23/25 (US)", "25/27 (US)", "27/30 (US)",
            "30/32 (US)", "32/34 (US)", "34/36 (US)", "36/40 (US)", "40+ (US)",
            "Extra Large", "Large", "Medium", "Small"
        ],
        "Packaging": [
            "Std Netted Bigbag (250-1000kg)", "Vacuum Bigbag (250-1000kg)",
            "Vac Bags in Carton (1-25kg)", "Alu Box (1-25kg)", "Nylon Sack (25-90kg)",
            "Gunny Sack (50-90kg)", "Tanker Truck", "Metal Drum (200L)",
            "Plastic Drum (60L)", "Plastic Bucket (1-25L)", "Metal Tin (5L)",
            "Retail Bag (Pillow)", "Retail Bag (Doybag)", "Retail Bag (Quadro)",
            "Glass Jar", "Small Bucket"
        ],
        "Currencies": ["SEK", "TL", "USD", "EUR", "NOK"],
        "Incoterms": ["EXW", "FCA", "CPT", "CIP", "DAP", "DPU", "DDP", "FAS", "FOB", "CFR", "CIF"]
    }

    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    workbook = writer.book
    
    # --- SHEET 1: OFFER SHEET ---
    worksheet = workbook.add_worksheet('Offer Sheet')
    worksheet.set_tab_color('#107C41')

    # Formats
    header_format = workbook.add_format({'bold': True, 'font_size': 14, 'color': '#203764'})
    label_format = workbook.add_format({'bold': True, 'align': 'right', 'bg_color': '#f2f2f2', 'border': 1})
    input_format = workbook.add_format({'border': 1, 'bg_color': '#ffffff'})
    table_header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1, 'text_wrap': True})
    
    # Formats for Quality Sheet
    linked_cell_format = workbook.add_format({'bg_color': '#E7E6E6', 'border': 1, 'italic': True, 'font_color': '#595959'})
    quality_header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#FFC000', 'font_color': 'black', 'border': 1, 'text_wrap': True})

    # --- MAIN SHEET LAYOUT ---
    worksheet.write('A1', 'AVELLA OFFER SHEET', header_format)
    headers = [
        ("Date:", "B3"), ("Offer No:", "D3"), ("Validity:", "F3"),
        ("Customer Name:", "B4"), ("Cust. Ref:", "D4"), ("Avella Ref:", "F4"),
        ("Payment Terms:", "B5"), ("Delivery Addr:", "D5")
    ]
    for label, cell in headers:
        worksheet.write(cell, label, label_format)
        col_letter = cell[0]
        row_num = int(cell[1:])
        input_cell = chr(ord(col_letter) + 1) + str(row_num)
        worksheet.write(input_cell, "", input_format)
    worksheet.merge_range('E5:G5', "", input_format)

    # Main Product Table Columns
    table_start_row = 8
    columns = [
        "Category", 
        "Product Group", 
        "Total Contract Volume (kg)",
        "Type/Process", 
        "Variety", 
        "Size",
        "Packaging", 
        "Net Wgt (kg)", 
        "Price", 
        "Currency", 
        "Incoterms",
        "Place of Delivery",
        "Minimum Order Quantity (kg)",
        "Shipment Schedule",
        "Payment Terms"
    ]
    
    for i, col_name in enumerate(columns):
        worksheet.write(table_start_row, i, col_name, table_header_format)
        worksheet.set_column(i, i, 15)
    
    # Adjust widths
    worksheet.set_column('B:B', 20)
    worksheet.set_column('C:C', 20)
    worksheet.set_column('D:D', 25)
    worksheet.set_column('E:E', 20)
    worksheet.set_column('G:G', 25)
    worksheet.set_column('L:L', 20)
    worksheet.set_column('M:M', 25)
    worksheet.set_column('N:N', 20)
    worksheet.set_column('O:O', 20)

    # --- SHEET 2: QUALITY PARAMETERS ---
    worksheet_qual = workbook.add_worksheet('Quality Parameters')
    worksheet_qual.set_tab_color('#FFC000')

    # Columns for Quality Sheet
    qual_ident_cols = ["Product Group (Linked)", "Type (Linked)", "Variety (Linked)", "Size (Linked)"]
    
    qual_param_cols = [
        "Target Humidity %",
        "Maximum FFA %",
        "Maximum Peroxide",
        "Maximum Oversize %",
        "Maximum Undersize %",
        "Maximum Visible Rotten %",
        "Maximum Hidden Rotten %",
        "Maximum Visible Mouldy %",
        "Maximum Hidden Mouldy %",
        "Maximum Visible Tumorous %",
        "Maximum Hidden Tumorous %",
        "Maximum Insect Damaged %",
        "Maximum Twin Kernels %",
        "Maximum Mech. Damaged %",
        "Maximum Broken %",
        "Maximum Rancid %",
        "Maximum Shrivelled %",
        "Maximum Other Types %",
        "Maximum Shell Pieces",
        "Maximum Foreign Matter"
    ]
    
    # --- DEFAULT VALUES ---
    default_qual_values = [
        "", 1, 1, 5, 5, 2, 2.5, 0.5, 0.5, 5, 5, 0, 2, 8, 4, 1, 2.5, 10, "0.01%", 0
    ]
    
    all_qual_cols = qual_ident_cols + qual_param_cols

    # Write Headers for Quality Sheet
    for i, col_name in enumerate(all_qual_cols):
        worksheet_qual.write(table_start_row, i, col_name, quality_header_format)
        worksheet_qual.set_column(i, i, 22) 

    # --- DATA & LINKING LOGIC ---
    start_row_idx = table_start_row + 1
    end_row_idx = 100

    for r in range(start_row_idx, end_row_idx):
        xl_row = r + 1
        # Linking Formulas
        worksheet_qual.write_formula(r, 0, f"='Offer Sheet'!B{xl_row}", linked_cell_format) 
        worksheet_qual.write_formula(r, 1, f"='Offer Sheet'!D{xl_row}", linked_cell_format) 
        worksheet_qual.write_formula(r, 2, f"='Offer Sheet'!E{xl_row}", linked_cell_format) 
        worksheet_qual.write_formula(r, 3, f"='Offer Sheet'!F{xl_row}", linked_cell_format) 
        
        for i, val in enumerate(default_qual_values):
            worksheet_qual.write(r, 4 + i, val, input_format)

    # --- REFERENCE DATA & VALIDATION (Main Sheet) ---
    ref_sheet = workbook.add_worksheet('ReferenceData')
    ref_sheet.hide()

    def write_list_to_ref(header, data_list, col_idx):
        ref_sheet.write(0, col_idx, header)
        for i, item in enumerate(data_list):
            ref_sheet.write(i + 1, col_idx, item)
        return f"=ReferenceData!${xlsxwriter.utility.xl_col_to_name(col_idx)}$2:${xlsxwriter.utility.xl_col_to_name(col_idx)}${len(data_list) + 1}"

    cat_range = write_list_to_ref("Categories", data["Categories"], 0)
    group_range = write_list_to_ref("Groups", data["Product_Groups"], 1)
    type_range = write_list_to_ref("Types", data["Product_Types"], 2)
    var_range = write_list_to_ref("Varieties", data["Varieties"], 3)
    size_range = write_list_to_ref("Sizes", data["Sizes"], 4)
    pack_range = write_list_to_ref("Packaging", data["Packaging"], 5)
    curr_range = write_list_to_ref("Currencies", data["Currencies"], 6)
    inco_range = write_list_to_ref("Incoterms", data["Incoterms"], 7)

    worksheet.data_validation(start_row_idx, 0, end_row_idx, 0, {'validate': 'list', 'source': cat_range})
    worksheet.data_validation(start_row_idx, 1, end_row_idx, 1, {'validate': 'list', 'source': group_range})
    worksheet.data_validation(start_row_idx, 3, end_row_idx, 3, {'validate': 'list', 'source': type_range})
    worksheet.data_validation(start_row_idx, 4, end_row_idx, 4, {'validate': 'list', 'source': var_range})
    worksheet.data_validation(start_row_idx, 5, end_row_idx, 5, {'validate': 'list', 'source': size_range})
    worksheet.data_validation(start_row_idx, 6, end_row_idx, 6, {'validate': 'list', 'source': pack_range})
    worksheet.data_validation(start_row_idx, 9, end_row_idx, 9, {'validate': 'list', 'source': curr_range})
    worksheet.data_validation(start_row_idx, 10, end_row_idx, 10, {'validate': 'list', 'source': inco_range})

    writer.close()
    output.seek(0)
    return output

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
                st.session_state.user = user
                st.session_state.role = user['role']
                st.success(f"Hoşgeldiniz, {user['email']} ({user['role']})")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(msg)

    with tab_register:
        st.caption("Sadece Müşteriler veya Yeni Personel için")
        new_email = st.text_input("E-posta", key="reg_email")
        new_pass = st.text_input("Şifre Belirleyin", type="password", key="reg_pass")
        new_pass_confirm = st.text_input("Şifre Tekrar", type="password", key="reg_pass2")
        reg_role = "customer"
        if "@avella" in new_email: 
            st.info("Avella personeli olarak algılandı (Otomatik Onay).")
            reg_role = "employee"
        if st.button("Kayıt Ol"):
            if new_pass != new_pass_confirm:
                st.error("Şifreler eşleşmiyor!")
            elif len(new_pass) < 6:
                st.error("Şifre en az 6 karakter olmalı.")
            else:
                success, msg = register_user(new_email, new_pass, role=reg_role)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

# ==========================================
# 🚀 MAIN APP (ROUTER LOGIC)
# ==========================================
else:
    user = st.session_state.user
    role = st.session_state.role
    
    st.sidebar.info(f"👤 {user['email']}")
    st.sidebar.caption(f"Rol: {role.upper()}")
    
    if st.sidebar.button("Çıkış Yap"):
        st.session_state.user = None
        st.session_state.role = None
        st.rerun()

    # --- MENU GENERATION ---
    available_menu_names = []
    
    if role == 'customer':
        available_menu_names = [CUSTOMER_PORTAL_NAME]
    elif role == 'administrator':
        available_menu_names = [CUSTOMER_PORTAL_NAME] 
        for mod_id in [1, 2, 3, 4, 5, 6]:
            if mod_id in MODULE_MAP:
                available_menu_names.append(MODULE_MAP[mod_id])
    elif role == 'employee':
        allowed_ids = user.get('allowed_modules', [])
        if allowed_ids is None: allowed_ids = []
        for mod_id in sorted(allowed_ids):
            if mod_id in MODULE_MAP:
                available_menu_names.append(MODULE_MAP[mod_id])

    if not available_menu_names:
        st.error("🚫 Yetkili olduğunuz modül bulunmamaktadır.")
        st.stop()
        
    module = st.sidebar.radio("Menü", available_menu_names)

    # ==========================
    # CUSTOMER PORTAL
    # ==========================
    if module == CUSTOMER_PORTAL_NAME:
        st.title(CUSTOMER_PORTAL_NAME)
        
        portal_tabs = ["Inshell Hazelnuts and Market Updates"]
        if role == 'administrator':
            portal_tabs.append("Avella Market Price Input (Admin)")
            
        tabs = st.tabs(portal_tabs)
        
        # --- TAB 1: CHARTS ---
        with tabs[0]:
            st.header("🌰 Market Updates & Inshell Prices")
            
            with st.expander("Currency Settings (Live Rates Simulation)", expanded=True):
                c1, c2 = st.columns(2)
                rate_usd = c1.number_input("Current USD/TL Rate", value=34.50, min_value=1.0, format="%.2f")
                rate_eur = c2.number_input("Current EUR/TL Rate", value=37.20, min_value=1.0, format="%.2f")
            
            st.caption(f"Charts below show historical TL prices converted using TODAY's rates: 1 USD = {rate_usd} TL, 1 EUR = {rate_eur} TL.")
            
            df_prices = get_market_prices()
            
            if not df_prices.empty:
                df_prices['date'] = pd.to_datetime(df_prices['date'])
                one_year_ago = datetime.now() - timedelta(days=365)
                df_prices = df_prices[df_prices['date'] >= one_year_ago]
                hazelnut_types = ["Tombul", "Cakildak", "Levant"]
                
                for h_type in hazelnut_types:
                    st.subheader(f"{h_type} Inshell Price Trends")
                    df_subset = df_prices[df_prices['hazelnut_type'] == h_type].sort_values('date')
                    
                    if not df_subset.empty:
                        trace_tl = go.Scatter(
                            x=df_subset['date'], y=df_subset['price_tl'], name=f"{h_type} (TL)",
                            line=dict(color='firebrick', width=3), mode='lines+markers'
                        )
                        trace_usd = go.Scatter(
                            x=df_subset['date'], y=df_subset['price_tl'] / rate_usd, name=f"{h_type} (USD)",
                            line=dict(color='royalblue', width=2, dash='dot'), yaxis='y2'
                        )
                        trace_eur = go.Scatter(
                            x=df_subset['date'], y=df_subset['price_tl'] / rate_eur, name=f"{h_type} (EUR)",
                            line=dict(color='green', width=2, dash='dot'), yaxis='y2'
                        )
                        
                        fig = go.Figure(data=[trace_tl, trace_usd, trace_eur])
                        # FIXED: Use nested dictionaries for title/font to ensure compatibility
                        fig.update_layout(
                            xaxis=dict(title="Date"),
                            yaxis=dict(
                                title=dict(text="Price (TL)", font=dict(color="firebrick")),
                                tickfont=dict(color="firebrick")
                            ),
                            yaxis2=dict(
                                title=dict(text="Price (USD / EUR)", font=dict(color="royalblue")),
                                tickfont=dict(color="royalblue"),
                                overlaying="y",
                                side="right"
                            ),
                            hovermode="x unified",
                            legend=dict(x=0, y=1.1, orientation="h")
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"No data for {h_type} in the last 365 days.")
            else:
                st.info("No market price data available yet.")

        # --- TAB 2: ADMIN INPUT ---
        if role == 'administrator' and len(tabs) > 1:
            with tabs[1]:
                st.header("📝 Input Daily Market Prices")
                with st.form("price_input_form"):
                    d_date = st.date_input("Date", value=datetime.now())
                    c1, c2, c3 = st.columns(3)
                    p_tombul = c1.number_input("Tombul (TL/kg)", min_value=0.0, step=0.5)
                    p_cakildak = c2.number_input("Cakildak (TL/kg)", min_value=0.0, step=0.5)
                    p_levant = c3.number_input("Levant (TL/kg)", min_value=0.0, step=0.5)
                    
                    if st.form_submit_button("Save Prices"):
                        data_to_insert = []
                        if p_tombul > 0: data_to_insert.append({"date": str(d_date), "hazelnut_type": "Tombul", "price_tl": p_tombul})
                        if p_cakildak > 0: data_to_insert.append({"date": str(d_date), "hazelnut_type": "Cakildak", "price_tl": p_cakildak})
                        if p_levant > 0: data_to_insert.append({"date": str(d_date), "hazelnut_type": "Levant", "price_tl": p_levant})
                        
                        if data_to_insert:
                            try:
                                supabase.table("market_prices").insert(data_to_insert).execute()
                                st.success("Prices Saved Successfully!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error saving: {e}")
                        else:
                            st.warning("Please enter at least one price.")
                
                st.markdown("### 📜 Historical Data Input")
                df_hist = get_market_prices()
                if not df_hist.empty:
                    st.dataframe(df_hist.sort_values(by='created_at', ascending=False), use_container_width=True)

    # ==========================
    # EXISTING MODULES 1-6
    # ==========================
    # MODÜL 1: ŞUBE ÜRÜN GİRİŞİ
    elif module == MODULE_MAP[1]:
        st.title("Modül 1: Şube Ürün Girişi")
        hazelnut_cat = "Kabuklu Fındık"
        st.info("Bu modül Şubelerden yapılan **Kabuklu Fındık** alımları içindir.")
        with st.form("sube_hazelnut_form"):
            st.subheader("1. Müstahsil & Tedarikçi")
            c1, c2, c3 = st.columns(3)
            supplier = c1.text_input("Tedarikçi Adı")
            sup_type = c2.selectbox("Tedarikçi Tipi", ["Müstahsil", "Tüccar", "Şirket"])
            id_num = c3.text_input("TCKN / VKN")
            c4, c5, c6 = st.columns(3)
            city = c4.text_input("İl"); dist_in = c5.text_input("İlçe"); vill_in = c6.text_input("Köy / Mahalle")
            c_cont, c_cert = st.columns(2)
            contact = c_cont.text_input("Telefon No")
            cert_status = c_cert.selectbox("Sertifikasyon", ["Yok", "Organik", "Rainforest Alliance", "Avella"])
            st.markdown("---")
            c7, c8, c9 = st.columns(3)
            reg_type = c7.selectbox("Alım Şekli", ["Satın Alma", "Emanet"])
            location = c8.selectbox("Teslimat Yeri", ["Fabrika", "Tarla", "Avella Şube"])
            hazelnut_type = c9.selectbox("Fındık Çeşidi", ["Karışık", "Giresun Tombul", "Çakıldak", "Kara", "Sivri", "Palaz", "Badem", "Foşa", "Yomra"])
            
            st.markdown("---")
            price_gross=0.0; price_net_deducted=0.0; val_randiman=0.0

            st.subheader("2. Kalite, Miktar ve Fiyatlandırma")
            col_q1, col_q2 = st.columns([1, 1])
            with col_q1:
                st.markdown("**Fiziksel Analiz (Eksper)**")
                w_sample = st.number_input("Kabuklu Numune Ağırlığı (g)", value=250.0)
                w_good = st.number_input("Sağlam İç (g)", 0.0)
                w_shriv = st.number_input("Buruşuk İç (g)", 0.0)
                w_vis_rot = st.number_input("Görünen Çürük (g)", 0.0)
                w_hid_rot = st.number_input("Gizli Çürük (g)", 0.0)
                w_tumor = st.number_input("Ur (g)", 0.0)
                s1, s2 = st.columns(2)
                w_over = s1.number_input("1. Numara İç - 13 mm üzeri (g)", 0.0)
                w_under = s2.number_input("Elek Altı İç - 9 mm altı (g)", 0.0)
                val_moist = st.number_input("Nem (%)", 0.0, 100.0, 5.0)
            
            with col_q2:
                st.markdown("**Miktar ve Fiyatlandırma**")
                net_weight = st.number_input("Toplam Net Ağırlık (kg)", min_value=0.0)
                st.caption("Paket Adetleri")
                p1, p2, p3 = st.columns(3)
                cnt_nylon = p1.number_input("Naylon", min_value=0)
                cnt_jute = p2.number_input("Jüt", min_value=0)
                cnt_bigbag = p3.number_input("Big Bag", min_value=0)
                st.markdown("---")
                if reg_type == "Emanet":
                    st.info("Emanet Alım: Fiyat 0 TL")
                    price_gross = 0.0
                else:
                    price_gross = st.number_input("Borsa Fiyatı (50 Randıman)", value=120.0)

            st.markdown("---")
            calc_pressed = st.form_submit_button("🔄 Randıman ve Fiyat Hesapla")
            val_randiman = calculate_randiman(w_sample, w_good, w_shriv)
            net_price_50 = price_gross / 1.0245
            unit_price = net_price_50 * (val_randiman / 50.0)
            total_val = unit_price * net_weight
            if calc_pressed:
                st.markdown("##### Analiz Sonuçları")
                st.metric("Randıman", f"%{val_randiman:.2f}")
                if reg_type != "Emanet": st.success(f"💰 **TOPLAM TUTAR:** {total_val:,.2f} TL")
            st.markdown("---")
            st.subheader("3. Ödeme ve Kayıt")
            f1, f2, f3 = st.columns(3)
            doc_num = f1.text_input("Makbuz / Fatura No")
            pay_amount = f2.number_input("Ödenen Tutar", 0.0)
            pay_method = f3.selectbox("Ödeme Yöntemi", ["Nakit", "Banka", "Çek"])
            if reg_type != "Emanet": st.metric("Kalan Bakiye", f"{total_val - pay_amount:,.2f} TL")

            if st.form_submit_button("✅ Şube Girişini Kaydet"):
                payload = {
                    "created_by": st.session_state.user['email'], "status": "Pending Arrival",
                    "category": hazelnut_cat, "supplier": supplier, "supplier_type": sup_type,
                    "id_number": id_num, "city": city, "district": dist_in, "village": vill_in,
                    "phone_number": contact, "cert_status": cert_status,
                    "reg_type": reg_type, "location": location, "item_type": hazelnut_type,
                    "qty_ordered": net_weight, "total_value": total_val, "document_number": doc_num,
                    "payment_amount": pay_amount, "remaining_balance": total_val - pay_amount,
                    "count_nylon": cnt_nylon, "count_jute": cnt_jute, "count_bigbag": cnt_bigbag,
                    "weight_sample": w_sample, "weight_good": w_good, "weight_shrivelled": w_shriv,
                    "weight_visible_rotten": w_vis_rot, "weight_hidden_rotten": w_hid_rot, 
                    "weight_tumor": w_tumor, "weight_undersize": w_under, "weight_oversize": w_over,
                    "moisture": val_moist, "calculated_randiman": val_randiman,
                    "gross_price_50": price_gross, "net_price_50": net_price_50, "actual_unit_price": unit_price
                }
                insert_record("purchases", payload)
                st.success("Şube Girişi Kaydedildi!")

    # MODÜL 2: FABRİKA ÜRÜN GİRİŞİ
    elif module == MODULE_MAP[2]:
        st.title("Modül 2: Fabrika Ürün Girişi")
        tab_findik, tab_malzeme, tab_genel = st.tabs(["🌰 Fındık Alımı", "📦 Malzeme Alımı", "⚙️ Makine & Hizmet"])
        with tab_findik:
            hazelnut_cat = st.selectbox("Fındık Kategorisi", ["Kabuklu Fındık", "İç Fındık", "İşlenmiş Fındık"], key="fab_findik_cat")
            with st.form("fab_hazelnut_form"):
                st.subheader("1. Müstahsil & Tedarikçi")
                c1, c2, c3 = st.columns(3)
                supplier = c1.text_input("Tedarikçi Adı")
                sup_type = c2.selectbox("Tedarikçi Tipi", ["Müstahsil", "Tüccar", "Şirket"])
                id_num = c3.text_input("TCKN / VKN")
                c4, c5, c6 = st.columns(3)
                city = c4.text_input("İl"); dist_in = c5.text_input("İlçe"); vill_in = c6.text_input("Köy / Mahalle")
                c_cont, c_cert = st.columns(2)
                contact = c_cont.text_input("Telefon No")
                cert_status = c_cert.selectbox("Sertifikasyon", ["Yok", "Organik", "Rainforest Alliance", "Avella"])
                st.markdown("---")
                c7, c8, c9 = st.columns(3)
                reg_type = c7.selectbox("Alım Şekli", ["Satın Alma", "Emanet"])
                location = c8.selectbox("Teslimat Yeri", ["Fabrika", "Tarla", "Avella Şube"])
                hazelnut_type = c9.selectbox("Fındık Çeşidi", ["Karışık", "Giresun Tombul", "Çakıldak", "Kara", "Sivri", "Palaz", "Badem", "Foşa", "Yomra"])
                st.markdown("---")
                st.subheader("2. Detaylı Kalite Analizi (Laboratuvar)")
                k1, k2, k3 = st.columns(3)
                label_sample = "Kabuklu Numune Ağırlığı (g)" if hazelnut_cat == "Kabuklu Fındık" else "İç Numune Ağırlığı (g)"
                w_sample = k1.number_input(label_sample, value=250.0 if hazelnut_cat == "Kabuklu Fındık" else 100.0)
                lab_cal = k2.selectbox("Kalibre", CALIBRE_OPTIONS)
                val_moist = k3.number_input("Nem (%)", 0.0, 100.0, 5.0)
                k4, k5 = st.columns(2)
                l_ffa = k4.number_input("FFA (%)", 0.0, 100.0, 0.0)
                l_perox = k5.number_input("Peroksit (meqO2/kg)", 0.0)

                st.markdown("##### B. Fiziksel Kusurlar (Gram)")
                r1c1, r1c2, r1c3, r1c4 = st.columns(4)
                w_good = r1c1.number_input("Sağlam İç (g)", 0.0)
                w_vis_rot = r1c2.number_input("Görünen Çürük (g)", 0.0)
                w_hid_rot = r1c3.number_input("Gizli Çürük (g)", 0.0)
                w_worm = r1c4.number_input("Kurt Yenikli (g)", 0.0)
                r2c1, r2c2, r2c3, r2c4 = st.columns(4)
                w_vis_mold = r2c1.number_input("Görünen Küflü (g)", 0.0)
                w_hid_mold = r2c2.number_input("Gizli Küflü (g)", 0.0)
                w_vis_tumor = r2c3.number_input("Görünen Urlu (g)", 0.0)
                w_hid_tumor = r2c4.number_input("Gizli Urlu (g)", 0.0)
                r3c1, r3c2, r3c3, r3c4 = st.columns(4)
                w_shriv = r3c1.number_input("Buruşuk İç (g)", 0.0)
                w_lemon = r3c2.number_input("Limoni (g)", 0.0)
                w_decayed = r3c3.number_input("Vurgun (g)", 0.0)
                w_broken = r3c4.number_input("Kırık (g)", 0.0)
                r4c1, r4c2, r4c3, r4c4 = st.columns(4)
                w_twin = r4c1.number_input("İkiz (g)", 0.0)
                w_other = r4c2.number_input("Diğer Tipler (g)", 0.0)
                w_under = r4c3.number_input("Elek Altı (g)", 0.0)
                w_over = r4c4.number_input("Elek Üstü (g)", 0.0)

                st.markdown("##### C. Yabancı Madde & Mikrobiyolojik")
                m1, m2, m3, m4 = st.columns(4)
                c_membrane = m1.number_input("Zar Atmayan Tane (adet)", 0)
                w_shell = m2.number_input("Kabuk (g)", 0.0)
                c_foreign = m3.number_input("Yabancı Madde (tane)", 0)
                size_1_g = 0.0; undersize_g = 0.0
                if hazelnut_cat == "Kabuklu Fındık":
                    st.markdown("##### D. Kabuklu Ekstra Boylama (Gram)")
                    ex1, ex2 = st.columns(2)
                    size_1_g = ex1.number_input("1. Numara İç - 13 mm üzeri (g)", 0.0)
                    undersize_g = ex2.number_input("Elek Altı İç - 9 mm altı (g)", 0.0)

                st.markdown("---")
                m_row2_1, m_row2_2, m_row2_3, m_row2_4 = st.columns(4)
                l_salm = m_row2_1.text_input("Salmonella")
                l_ecoli = m_row2_2.text_input("E. Coli")
                l_b1 = m_row2_3.number_input("Aflatoksin B1 (ppb)", 0.0)
                l_tot = m_row2_4.number_input("Aflatoksin Total (ppb)", 0.0)

                st.markdown("---")
                calc_btn = st.form_submit_button("📊 Rapor Oluştur")
                val_randiman = calculate_randiman(w_sample, w_good, w_shriv)
                
                if calc_btn:
                    st.info("📊 **Canlı Analiz Raporu**")
                    calc_inputs = {
                        "Sağlam İç": w_good, "Görünen Çürük": w_vis_rot, "Gizli Çürük": w_hid_rot, 
                        "Görünen Küflü": w_vis_mold, "Gizli Küflü": w_hid_mold,
                        "Görünen Urlu": w_vis_tumor, "Gizli Urlu": w_hid_tumor,
                        "Kurt Yenikli": w_worm, "Buruşuk İç": w_shriv, "Limoni": w_lemon,
                        "Vurgun": w_decayed, "Kırık": w_broken, "İkiz": w_twin, 
                        "Diğer Tipler": w_other, "Elek Altı": w_under, "Elek Üstü": w_over, "Kabuk": w_shell
                    }
                    report_data = []
                    if w_sample > 0:
                        for k, v in calc_inputs.items():
                            pct = (v / w_sample) * 100
                            if v > 0: report_data.append({"Parametre": k, "Girdi (g)": f"{v} g", "Sonuç": f"%{pct:.2f}"})
                        if hazelnut_cat == "Kabuklu Fındık":
                            if size_1_g > 0: report_data.append({"Parametre": "1. Numara (13mm+)", "Girdi (g)": f"{size_1_g} g", "Sonuç": f"%{(size_1_g/w_sample)*100:.2f}"})
                            if undersize_g > 0: report_data.append({"Parametre": "Elek Altı (9mm-)", "Girdi (g)": f"{undersize_g} g", "Sonuç": f"%{(undersize_g/w_sample)*100:.2f}"})
                        if val_moist > 0: report_data.append({"Parametre": "Nem", "Girdi (g)": "-", "Sonuç": f"%{val_moist}"})
                        if l_ffa > 0: report_data.append({"Parametre": "FFA", "Girdi (g)": "-", "Sonuç": f"%{l_ffa}"})
                        if l_perox > 0: report_data.append({"Parametre": "Peroksit", "Girdi (g)": "-", "Sonuç": f"{l_perox} meq"})
                    if report_data: st.dataframe(pd.DataFrame(report_data), use_container_width=True)
                    else: st.warning("Rapor için değer giriniz.")

                st.markdown("---")
                st.subheader("Miktar ve Fiyatlandırma")
                cq1, cq2 = st.columns(2)
                with cq1:
                    net_weight = st.number_input("Toplam Net Ağırlık (kg)", min_value=0.0)
                    st.caption("Paketleme Detayları")
                    p1, p2, p3 = st.columns(3)
                    cnt_nylon = p1.number_input("Naylon", min_value=0)
                    cnt_jute = p2.number_input("Jüt", min_value=0)
                    cnt_bigbag = p3.number_input("Big Bag", min_value=0)
                if reg_type == "Emanet":
                    total_val = 0.0; price_gross = 0.0; price_net_deducted = 0.0
                else:
                    with cq2:
                        if hazelnut_cat == "Kabuklu Fındık":
                            price_gross = st.number_input("Borsa Fiyatı (50 Randıman)", value=120.0)
                            net_price_50 = price_gross / 1.0245
                            price_net_deducted = net_price_50 * (val_randiman / 50.0)
                            if calc_btn: st.info(f"Hesaplanan Randıman: %{val_randiman:.2f}")
                        else:
                            price_gross = st.number_input("Gösterge Fiyatı (TL)", min_value=0.0)
                            price_net_deducted = st.number_input("Net Fiyat (TL)", min_value=0.0)
                        total_val = price_net_deducted * net_weight
                        st.success(f"**TOPLAM TUTAR:** {total_val:,.2f} TL")
                st.markdown("---")
                st.subheader("3. Ödeme ve Kayıt")
                f1, f2, f3 = st.columns(3)
                doc_num = f1.text_input("Makbuz / Fatura No")
                pay_amount = f2.number_input("Ödenen Tutar", 0.0)
                pay_method = f3.selectbox("Ödeme Yöntemi", ["Nakit", "Banka", "Çek"])
                if reg_type != "Emanet": st.metric("Kalan Bakiye", f"{total_val - pay_amount:,.2f} TL")

                if st.form_submit_button("✅ Fabrika Girişini Kaydet"):
                    payload = {
                        "created_by": st.session_state.user['email'], "status": "Pending Arrival",
                        "category": hazelnut_cat, "supplier": supplier, "supplier_type": sup_type,
                        "id_number": id_num, "city": city, "district": dist_in, "village": vill_in,
                        "phone_number": contact, "cert_status": cert_status,
                        "reg_type": reg_type, "location": location, "item_type": hazelnut_type,
                        "qty_ordered": net_weight, "total_value": total_val, "document_number": doc_num,
                        "payment_amount": pay_amount, "remaining_balance": total_val - pay_amount,
                        "count_nylon": cnt_nylon, "count_jute": cnt_jute, "count_bigbag": cnt_bigbag,
                        "weight_sample": w_sample, "weight_good": w_good, "weight_shrivelled": w_shriv,
                        "weight_visible_rotten": w_vis_rot, "weight_hidden_rotten": w_hid_rot, 
                        "weight_tumor": w_tumor, "weight_undersize": w_under, "weight_oversize": w_over,
                        "moisture": val_moist, "calculated_randiman": val_randiman,
                        "gross_price_50": price_gross, "actual_unit_price": price_net_deducted
                    }
                    insert_record("purchases", payload)
                    st.success("Fabrika Girişi Kaydedildi!")

        with tab_malzeme:
            st.subheader("Malzeme Seçimi")
            material_cats = ["Ambalaj Malzemeleri", "Bakım Malzemeleri", "Ofis Malzemeleri", "Temizlik Malzemeleri", "Eşantiyon & Hediye", "İş Kıyafetleri", "Gıda ve Mutfak", "Diğer"]
            c_cat, c_item = st.columns(2)
            selected_mat_cat = c_cat.selectbox("Kategori", material_cats, key="mat_cat_fab")
            try:
                response = supabase.table("material_definitions").select("*").eq("category", selected_mat_cat).execute()
                items_data = response.data
                item_names = [row['item_name'] for row in items_data]
            except: items_data = []; item_names = []
            if item_names:
                selected_item_name = c_item.selectbox("Malzeme Seç", item_names, key="mat_item_fab")
                selected_item_data = next((item for item in items_data if item["item_name"] == selected_item_name), None)
                if selected_item_data:
                    with st.expander("ℹ️ Özellikler", expanded=True):
                        sp1, sp2, sp3 = st.columns(3)
                        sp1.write(f"**Materyal:** {selected_item_data.get('mat_type', '-')}")
                        sp2.write(f"**Birim:** {selected_item_data.get('sales_unit', '-')} ({selected_item_data.get('unit_quantity', 1)})")
                        sp3.caption(f"Notlar: {selected_item_data.get('notes', '-')}")
            else:
                c_item.warning("Tanımlı malzeme yok.")
                selected_item_name = c_item.text_input("Manuel Giriş", key="mat_manual_fab")
            with st.form("fab_material_purchase"):
                supplier = st.text_input("Tedarikçi")
                c3, c4 = st.columns(2)
                qty = c3.number_input("Miktar", min_value=1.0)
                price = c4.number_input("Tutar (TL)", min_value=0.0)
                if st.form_submit_button("✅ Kaydet"):
                    payload = {"category": "Malzeme", "supplier": supplier, "item_type": selected_item_name, "item_sub_type": selected_mat_cat, "qty_ordered": qty, "total_value": price, "status": "Pending Arrival", "created_by": st.session_state.user['email']}
                    insert_record("purchases", payload)
                    st.success("Kaydedildi!")

        with tab_genel:
            st.subheader("Genel Alım")
            general_type = st.selectbox("Tür", ["Makine", "Hizmet"], key="gen_type_fab")
            with st.form("fab_gen_form"):
                c1, c2 = st.columns(2)
                supplier = c1.text_input("Firma")
                desc = c2.text_input("Açıklama")
                c3, c4 = st.columns(2)
                qty = c3.number_input("Miktar", 1.0)
                price = c4.number_input("Tutar", 0.0)
                if st.form_submit_button("✅ Kaydet"):
                    insert_record("purchases", {"category": general_type, "supplier": supplier, "item_type": desc, "qty_ordered": qty, "total_value": price, "status": "Pending Arrival", "created_by": st.session_state.user['email']})
                    st.success("Kaydedildi!")

    # MODÜL 3: MAL KABUL
    elif module == MODULE_MAP[3]:
        st.title("Modül 3: Mal Kabul (Kantar)")
        try:
            response = supabase.table("purchases").select("*").eq("status", "Pending Arrival").execute()
            pending_df = pd.DataFrame(response.data)
            if not pending_df.empty:
                st.dataframe(pending_df[["id", "supplier", "item_type", "qty_ordered", "location"]])
                po_ids = pending_df['id'].tolist()
                selected_id = st.selectbox("Sipariş Seç (ID)", po_ids)
                row = pending_df[pending_df['id'] == selected_id].iloc[0]
                st.info(f"Giriş: {row['item_type']} - {row['supplier']}")
                with st.form("intake"):
                    c1, c2 = st.columns(2)
                    plate = c1.text_input("Plaka")
                    waybill = c2.text_input("İrsaliye")
                    qty = st.number_input("Kantar Net", value=float(row['qty_ordered'] or 0))
                    loc = st.text_input("Depo")
                    if st.form_submit_button("Onayla"):
                        supabase.table("purchases").update({"status": "Received"}).eq("id", selected_id).execute()
                        insert_record("intake_log", {"po_id": int(selected_id), "plate_number": plate, "waybill_no": waybill, "received_qty": qty, "location_in_warehouse": loc, "created_by": st.session_state.user['email']})
                        insert_record("stock_movements", {"item_name": row['item_type'], "category": row.get('category'), "quantity": qty, "move_type": "Intake", "location": loc, "created_by": st.session_state.user['email']})
                        st.success("Giriş Yapıldı!"); time.sleep(1); st.rerun()
            else: st.info("Bekleyen yok.")
        except Exception as e: st.error(f"Hata: {e}")

    # MODÜL 4: YÖNETİCİ
    elif module == MODULE_MAP[4]:
        st.title("🛠️ Yönetici Ayarları")
        tab_users, tab_mat = st.tabs(["👥 Kullanıcı Yönetimi", "📦 Malzeme Tanımları"])
        
        with tab_users:
            st.subheader("Kullanıcı İzinleri ve Onay")
            all_users = get_all_users()
            df_users = pd.DataFrame(all_users)
            if not df_users.empty:
                st.dataframe(df_users[['email', 'role', 'is_approved', 'allowed_modules']], use_container_width=True)
                st.markdown("---")
                user_list = {u['email']: u for u in all_users}
                selected_email = st.selectbox("Kullanıcı Seç", list(user_list.keys()))
                if selected_email:
                    target_user = user_list[selected_email]
                    with st.form("edit_user_perm"):
                        st.write(f"**Seçili:** {target_user['email']}")
                        current_role = target_user['role']
                        role_options = ["customer", "employee", "administrator"]
                        try: role_idx = role_options.index(current_role)
                        except ValueError: role_idx = 0
                        new_role = st.selectbox("Rol", role_options, index=role_idx)
                        new_approved = st.checkbox("Onaylı Hesap", value=target_user['is_approved'])
                        current_modules = target_user.get('allowed_modules') or []
                        st.caption("Erişilebilir Modüller (Sadece 'employee' rolü için geçerlidir. 'administrator' hepsine erişir.)")
                        c1, c2, c3, c4, c5, c6 = st.columns(6)
                        m1 = c1.checkbox("1. Şube", 1 in current_modules)
                        m2 = c2.checkbox("2. Fabrika", 2 in current_modules)
                        m3 = c3.checkbox("3. Mal Kabul", 3 in current_modules)
                        m4 = c4.checkbox("4. Yönetici", 4 in current_modules)
                        m5 = c5.checkbox("5. Stok", 5 in current_modules)
                        m6 = c6.checkbox("6. Teklifler", 6 in current_modules)
                        
                        if st.form_submit_button("💾 Yetkileri Güncelle"):
                            new_mod_list = []
                            if m1: new_mod_list.append(1)
                            if m2: new_mod_list.append(2)
                            if m3: new_mod_list.append(3)
                            if m4: new_mod_list.append(4)
                            if m5: new_mod_list.append(5)
                            if m6: new_mod_list.append(6)
                            if update_user_permissions(target_user['id'], new_approved, new_mod_list, new_role):
                                st.success("Güncellendi!"); time.sleep(1); st.rerun()
                            else: st.error("Hata.")

        with tab_mat:
            cats = ["Ambalaj Malzemeleri", "Bakım Malzemeleri", "Ofis Malzemeleri", "Temizlik Malzemeleri", "Eşantiyon & Hediye", "İş Kıyafetleri", "Gıda ve Mutfak", "Diğer"]
            units = ['adet', 'gr', 'kg', 'bobin', 'rulo', 'paket', 'deste', 'palet', 'litre', 'mililitre', 'metreküp', 'desimetreküp', 'santimetreküp', 'metre', 'desimetre', 'santimetre', 'milimetre', 'bigbag', 'kamyon', 'tır', 'tank', 'metrekare', 'santimetrekare', 'ar', 'dekar', 'hektar']
            with st.expander("Listeyi Gör"):
                data = supabase.table("material_definitions").select("*").execute().data
                st.dataframe(pd.DataFrame(data), use_container_width=True)
            st.markdown("---")
            st.write("### ➕ Ekle / ✏️ Düzenle / 🗑️ Sil")
            action = st.radio("İşlem", ["Ekle", "Düzenle", "Sil"], horizontal=True)
            if action == "Ekle":
                with st.form("add_mat"):
                    c1, c2 = st.columns(2)
                    cat = c1.selectbox("Kategori", cats)
                    name = c2.text_input("Ad")
                    u1, u2 = st.columns(2)
                    unit = u1.selectbox("Birim", units)
                    uq = u2.number_input("Birim İçi Adet", 1.0)
                    nt = st.text_area("Notlar")
                    o1, o2, o3 = st.columns(3)
                    dim_o = o1.text_input("Dış Boyutlar")
                    dim_i = o2.text_input("İç Boyutlar")
                    w_g = o3.number_input("Ağırlık (g)", 0.0)
                    g1, g2, g3 = st.columns(3)
                    use = g1.text_input("Kullanım"); mat = g2.text_input("Materyal"); oth = g3.text_input("Diğer")
                    if st.form_submit_button("Kaydet"):
                        insert_record("material_definitions", {"category": cat, "item_name": name, "sales_unit": unit, "unit_quantity": uq, "notes": nt, "dim_outer": dim_o, "dim_inner": dim_i, "unit_weight_g": w_g, "use_case": use, "mat_type": mat, "other_specs": oth})
                        st.success("Eklendi!")
            elif action == "Düzenle":
                sel_cat = st.selectbox("Kategori", cats)
                items = supabase.table("material_definitions").select("*").eq("category", sel_cat).execute().data
                if items:
                    target = st.selectbox("Malzeme", [i['item_name'] for i in items])
                    row = next(i for i in items if i['item_name'] == target)
                    with st.form("edit_mat"):
                        new_name = st.text_input("Ad", row['item_name'])
                        e1, e2, e3 = st.columns(3)
                        emat = e1.text_input("Materyal", row.get('mat_type'))
                        euse = e2.text_input("Kullanım", row.get('use_case'))
                        eunit = e3.selectbox("Birim", units, index=units.index(row.get('sales_unit')) if row.get('sales_unit') in units else 0)
                        enote = st.text_area("Notlar", row.get('notes'))
                        if st.form_submit_button("Güncelle"):
                            supabase.table("material_definitions").update({"item_name": new_name, "mat_type": emat, "use_case": euse, "sales_unit": eunit, "notes": enote}).eq("id", row['id']).execute()
                            st.success("Güncellendi!")
            elif action == "Sil":
                sel_cat = st.selectbox("Kategori (Sil)", cats)
                items = supabase.table("material_definitions").select("*").eq("category", sel_cat).execute().data
                if items:
                    target = st.selectbox("Silinecek", [i['item_name'] for i in items])
                    if st.button("Sil"):
                        supabase.table("material_definitions").delete().eq("item_name", target).execute()
                        st.success("Silindi!")

    # MODÜL 5: STOK
    elif module == MODULE_MAP[5]:
        st.title("📦 Stok")
        moves = supabase.table("stock_movements").select("*").execute().data
        df = pd.DataFrame(moves)
        if not df.empty:
            stock = df.groupby('item_name')['quantity'].sum().reset_index()
            st.dataframe(stock, use_container_width=True)
            st.markdown("---")
            st.dataframe(df.sort_values(by='created_at', ascending=False))
        else: st.info("Hareket yok.")

    # MODÜL 6: TEKLIFLER (NEW)
    elif module == MODULE_MAP[6]:
        st.title("📄 Teklif Hazırlama (Offers)")
        st.info("Aşağıdaki butona tıklayarak boş bir Excel teklif şablonu oluşturabilirsiniz.")
        
        col_d1, col_d2 = st.columns([1, 2])
        with col_d1:
            if st.button("Excel Şablonu Oluştur"):
                with st.spinner("Excel dosyası hazırlanıyor..."):
                    excel_data = generate_offer_excel()
                    
                    st.download_button(
                        label="📥 İndir (Avella_Offer_Sheet.xlsx)",
                        data=excel_data,
                        file_name="Avella_Offer_Sheet.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    st.success("Dosya hazır! İndirme butonuna basınız.")
