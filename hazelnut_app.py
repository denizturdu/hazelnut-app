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

def calculate_percentages(base_w, inputs):
    results = {}
    if base_w == 0: return {k: 0.0 for k in inputs}
    for k, v in inputs.items(): results[k] = (v / base_w) * 100
    return results

def get_market_prices():
    """Fetch ALL market prices."""
    try:
        response = supabase.table("market_prices").select("*").order("date", desc=False).limit(3000).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
        return df
    except:
        return pd.DataFrame()

def get_live_rates():
    """Fetches live USD/TRY and EUR/TRY rates from a public API."""
    rates = {"USD": 34.50, "EUR": 37.20} 
    try:
        url = "https://open.er-api.com/v6/latest/TRY"
        resp = requests.get(url, timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            if "rates" in data:
                usd_val = data["rates"].get("USD")
                eur_val = data["rates"].get("EUR")
                if usd_val: rates["USD"] = 1 / usd_val
                if eur_val: rates["EUR"] = 1 / eur_val
    except:
        pass
    return rates

def log_login(email):
    """Inserts a record into the login_logs table."""
    try:
        supabase.table("login_logs").insert({"email": email}).execute()
    except Exception as e:
        print(f"Login log error: {e}")

def generate_offer_excel():
    """Generates the Offer Excel file in memory."""
    output = io.BytesIO()
    data = {
        "Categories": ["Nuts", "Dried Fruit", "Oil", "Chocolate"],
        "Product_Groups": ["Hazelnuts", "Walnuts", "Pistachios", "Almonds", "Peanuts"],
        "Product_Types": ["Inshell", "Natural Kernels", "Blanched Kernels", "Roasted Kernels"],
        "Varieties": ["Tombul", "Levant", "Cakildak"],
        "Sizes": ["11-13mm", "13-15mm", "9-11mm"],
        "Packaging": ["Bigbag", "Sack", "Vacuum"],
        "Currencies": ["USD", "EUR", "TL"],
        "Incoterms": ["FCA", "DAP", "CIF"]
    } # Simplified for brevity, logic remains valid
    
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
    headers = [("Date:", "B3"), ("Offer No:", "D3"), ("Validity:", "F3"), ("Customer Name:", "B4"), ("Cust. Ref:", "D4"), ("Avella Ref:", "F4"), ("Payment Terms:", "B5"), ("Delivery Addr:", "D5")]
    for label, cell in headers:
        worksheet.write(cell, label, label_format); col_letter = cell[0]; row_num = int(cell[1:]); input_cell = chr(ord(col_letter) + 1) + str(row_num); worksheet.write(input_cell, "", input_format)
    worksheet.merge_range('E5:G5', "", input_format)

    table_start_row = 8
    columns = ["Category", "Product Group", "Total Contract Volume (kg)", "Type/Process", "Variety", "Size", "Packaging", "Net Wgt (kg)", "Price", "Currency", "Incoterms", "Place of Delivery", "Minimum Order Quantity (kg)", "Shipment Schedule", "Payment Terms"]
    for i, col_name in enumerate(columns): worksheet.write(table_start_row, i, col_name, table_header_format); worksheet.set_column(i, i, 15)
    
    worksheet.set_column('B:B', 20); worksheet.set_column('C:C', 20); worksheet.set_column('D:D', 25); worksheet.set_column('E:E', 20); worksheet.set_column('G:G', 25); worksheet.set_column('L:L', 20); worksheet.set_column('M:M', 25); worksheet.set_column('N:N', 20); worksheet.set_column('O:O', 20)

    worksheet_qual = workbook.add_worksheet('Quality Parameters'); worksheet_qual.set_tab_color('#FFC000')
    qual_ident_cols = ["Product Group (Linked)", "Type (Linked)", "Variety (Linked)", "Size (Linked)"]
    qual_param_cols = ["Target Humidity %", "Maximum FFA %", "Maximum Peroxide", "Maximum Oversize %", "Maximum Undersize %", "Maximum Visible Rotten %", "Maximum Hidden Rotten %", "Maximum Visible Mouldy %", "Maximum Hidden Mouldy %", "Maximum Visible Tumorous %", "Maximum Hidden Tumorous %", "Maximum Insect Damaged %", "Maximum Twin Kernels %", "Maximum Mech. Damaged %", "Maximum Broken %", "Maximum Rancid %", "Maximum Shrivelled %", "Maximum Other Types %", "Maximum Shell Pieces", "Maximum Foreign Matter"]
    default_qual_values = ["", 1, 1, 5, 5, 2, 2.5, 0.5, 0.5, 5, 5, 0, 2, 8, 4, 1, 2.5, 10, "0.01%", 0]; all_qual_cols = qual_ident_cols + qual_param_cols
    for i, col_name in enumerate(all_qual_cols): worksheet_qual.write(table_start_row, i, col_name, quality_header_format); worksheet_qual.set_column(i, i, 22) 
    for r in range(table_start_row + 1, 100):
        xl_row = r + 1; worksheet_qual.write_formula(r, 0, f"='Offer Sheet'!B{xl_row}", linked_cell_format); worksheet_qual.write_formula(r, 1, f"='Offer Sheet'!D{xl_row}", linked_cell_format); worksheet_qual.write_formula(r, 2, f"='Offer Sheet'!E{xl_row}", linked_cell_format); worksheet_qual.write_formula(r, 3, f"='Offer Sheet'!F{xl_row}", linked_cell_format)
        for i, val in enumerate(default_qual_values): worksheet_qual.write(r, 4 + i, val, input_format)
    
    ref_sheet = workbook.add_worksheet('ReferenceData'); ref_sheet.hide()
    def write_list_to_ref(header, data_list, col_idx):
        ref_sheet.write(0, col_idx, header); [ref_sheet.write(i + 1, col_idx, item) for i, item in enumerate(data_list)]; return f"=ReferenceData!${xlsxwriter.utility.xl_col_to_name(col_idx)}$2:${xlsxwriter.utility.xl_col_to_name(col_idx)}${len(data_list) + 1}"
    
    cat_range = write_list_to_ref("Categories", data["Categories"], 0); group_range = write_list_to_ref("Product_Groups", data["Product_Groups"], 1); type_range = write_list_to_ref("Product_Types", data["Product_Types"], 2); var_range = write_list_to_ref("Varieties", data["Varieties"], 3); size_range = write_list_to_ref("Sizes", data["Sizes"], 4); pack_range = write_list_to_ref("Packaging", data["Packaging"], 5); curr_range = write_list_to_ref("Currencies", data["Currencies"], 6); inco_range = write_list_to_ref("Incoterms", data["Incoterms"], 7)
    
    worksheet.data_validation(table_start_row + 1, 0, 100, 0, {'validate': 'list', 'source': cat_range})
    worksheet.data_validation(table_start_row + 1, 1, 100, 1, {'validate': 'list', 'source': group_range})
    worksheet.data_validation(table_start_row + 1, 3, 100, 3, {'validate': 'list', 'source': type_range})
    worksheet.data_validation(table_start_row + 1, 4, 100, 4, {'validate': 'list', 'source': var_range})
    worksheet.data_validation(table_start_row + 1, 5, 100, 5, {'validate': 'list', 'source': size_range})
    worksheet.data_validation(table_start_row + 1, 6, 100, 6, {'validate': 'list', 'source': pack_range})
    worksheet.data_validation(table_start_row + 1, 9, 100, 9, {'validate': 'list', 'source': curr_range})
    worksheet.data_validation(table_start_row + 1, 10, 100, 10, {'validate': 'list', 'source': inco_range})

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
                # LOG LOGIN
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

    available_menu_names = []
    if role == 'customer': available_menu_names = [CUSTOMER_PORTAL_NAME]
    elif role == 'administrator':
        available_menu_names = [CUSTOMER_PORTAL_NAME]
        for mod_id in [1, 2, 3, 4, 5, 6]: 
            if mod_id in MODULE_MAP: available_menu_names.append(MODULE_MAP[mod_id])
    elif role == 'employee':
        allowed_ids = user.get('allowed_modules', [])
        if allowed_ids is None: allowed_ids = []
        for mod_id in sorted(allowed_ids):
            if mod_id in MODULE_MAP: available_menu_names.append(MODULE_MAP[mod_id])

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
        
        # --- TAB 1: CHARTS ---
        with tabs[0]:
            st.header("🌰 Market Updates & Inshell Prices")
            df_prices = get_market_prices()
            
            # Live Rates Header
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
                            if mode_type == 'TL':
                                y_vals = df_prices[col_name]
                            elif mode_type == 'USD':
                                y_vals = df_prices[col_name] / df_prices['rate_usd_try']
                            elif mode_type == 'EUR':
                                y_vals = df_prices[col_name] / df_prices['rate_eur_try']
                            
                            fig.add_trace(go.Scatter(
                                x=df_prices['date'], y=y_vals, name=h_type,
                                line=dict(color=colors[h_type], width=3),
                                mode='lines', fill=None
                            ))
                    fig.update_layout(
                        title=title,
                        xaxis=dict(title="Date", rangeslider=dict(visible=True), type="date", range=[start_window, max_db_date]),
                        yaxis=dict(title=dict(text=y_label, font=dict(color="black"))),
                        hovermode="x unified", height=500
                    )
                    return fig

                st.plotly_chart(build_chart("1. Inshell Prices (TL/kg)", 'TL', "Price (TL)"), use_container_width=True)
                st.plotly_chart(build_chart("2. Inshell Prices (USD/kg)", 'USD', "Price (USD)"), use_container_width=True)
                st.plotly_chart(build_chart("3. Inshell Prices (EUR/kg)", 'EUR', "Price (EUR)"), use_container_width=True)
            else:
                st.info("No market price data available yet.")

        # --- TAB 2: ADMIN INPUT ---
        if role == 'administrator' and len(tabs) > 1:
            with tabs[1]:
                st.header("📝 Input Daily Market Prices")
                live_rates = get_live_rates()
                default_usd = live_rates.get("USD", 0.0)
                default_eur = live_rates.get("EUR", 0.0)

                with st.form("price_input_form"):
                    d_date = st.date_input("Date", value=datetime.now())
                    st.caption("Enter prices for ALL 3 types (TL/kg).")
                    c1, c2, c3 = st.columns(3)
                    p_tombul = c1.number_input("Tombul", min_value=0.0, step=0.5)
                    p_cakildak = c2.number_input("Cakildak", min_value=0.0, step=0.5)
                    p_levant = c3.number_input("Levant", min_value=0.0, step=0.5)
                    st.markdown("---")
                    st.write("**Exchange Rates (Auto-fetched)**")
                    c4, c5 = st.columns(2)
                    r_usd = c4.number_input("USD/TRY Rate", min_value=0.0, step=0.01, format="%.4f", value=default_usd)
                    r_eur = c5.number_input("EUR/TRY Rate", min_value=0.0, step=0.01, format="%.4f", value=default_eur)
                    
                    if st.form_submit_button("Save Entry"):
                        if p_tombul > 0 and p_cakildak > 0 and p_levant > 0:
                            payload = {
                                "date": str(d_date),
                                "price_tombul": p_tombul,
                                "price_cakildak": p_cakildak,
                                "price_levant": p_levant,
                                "rate_usd_try": r_usd,
                                "rate_eur_try": r_eur,
                                "created_by": st.session_state.user['email']
                            }
                            try:
                                supabase.table("market_prices").upsert(payload, on_conflict="date").execute()
                                st.success("Entry Saved Successfully!")
                                time.sleep(1); st.rerun()
                            except Exception as e: st.error(f"Error: {e}")
                        else: st.warning("Please fill all price fields.")
                
                st.markdown("### 📜 Historical Data Input")
                df_hist = get_market_prices()
                if not df_hist.empty:
                    disp_cols = ["id", "date", "price_tombul", "price_cakildak", "price_levant", "rate_usd_try", "rate_eur_try", "created_by"]
                    valid_cols = [c for c in disp_cols if c in df_hist.columns]
                    st.dataframe(
                        df_hist[valid_cols].sort_values(by='date', ascending=False).style.format({
                            "price_tombul": "{:.2f}", "price_cakildak": "{:.2f}", "price_levant": "{:.2f}",
                            "rate_usd_try": "{:.4f}", "rate_eur_try": "{:.4f}"
                        }),
                        use_container_width=True, hide_index=True
                    )

    # MODÜL 1-6
    elif module == MODULE_MAP[1]:
        st.title("Modül 1: Şube Ürün Girişi"); hazelnut_cat = "Kabuklu Fındık"; st.info("Bu modül Şubelerden yapılan **Kabuklu Fındık** alımları içindir."); 
        with st.form("sube_hazelnut_form"):
            st.subheader("1. Müstahsil & Tedarikçi"); c1, c2, c3 = st.columns(3); supplier = c1.text_input("Tedarikçi Adı"); sup_type = c2.selectbox("Tedarikçi Tipi", ["Müstahsil", "Tüccar", "Şirket"]); id_num = c3.text_input("TCKN / VKN"); c4, c5, c6 = st.columns(3); city = c4.text_input("İl"); dist_in = c5.text_input("İlçe"); vill_in = c6.text_input("Köy / Mahalle"); c_cont, c_cert = st.columns(2); contact = c_cont.text_input("Telefon No"); cert_status = c_cert.selectbox("Sertifikasyon", ["Yok", "Organik", "Rainforest Alliance", "Avella"]); st.markdown("---"); c7, c8, c9 = st.columns(3); reg_type = c7.selectbox("Alım Şekli", ["Satın Alma", "Emanet"]); location = c8.selectbox("Teslimat Yeri", ["Fabrika", "Tarla", "Avella Şube"]); hazelnut_type = c9.selectbox("Fındık Çeşidi", ["Karışık", "Giresun Tombul", "Çakıldak", "Kara", "Sivri", "Palaz", "Badem", "Foşa", "Yomra"]); st.markdown("---"); price_gross=0.0; price_net_deducted=0.0; val_randiman=0.0; st.subheader("2. Kalite, Miktar ve Fiyatlandırma"); col_q1, col_q2 = st.columns([1, 1])
            with col_q1: st.markdown("**Fiziksel Anal
