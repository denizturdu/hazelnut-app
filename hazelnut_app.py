import streamlit as st
import pandas as pd
from db_utils import supabase, login_user, register_user, insert_record, get_all_users, update_user_permissions
import time
import io
import xlsxwriter

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
    6: "6. Teklifler (Offers)"  # <-- NEW MODULE
}

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

def generate_offer_excel():
    """Generates the Offer Excel file in memory."""
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
            "15-16mm", "14-15mm", "13-14mm", "12-14mm", "12-13mm", "11-13mm", "11-12mm",
            "10-12mm", "10-11mm", "9-11mm", "9-10mm", "9mm-", "9mm+", "0-2mm", "1-3mm",
            "2-4mm", "4-6mm", "5-7mm", "6-8mm", "7-11mm", "3-11mm", "5-11mm",
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
    worksheet = workbook.add_worksheet('Offer Sheet')
    worksheet.set_tab_color('#107C41')

    # Formats
    header_format = workbook.add_format({'bold': True, 'font_size': 14, 'color': '#203764'})
    label_format = workbook.add_format({'bold': True, 'align': 'right', 'bg_color': '#f2f2f2', 'border': 1})
    input_format = workbook.add_format({'border': 1, 'bg_color': '#ffffff'})
    table_header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1, 'text_wrap': True})

    # Header Section
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

    # Product Table
    table_start_row = 8
    columns = [
        "Category", "Product Group", "Type/Process", "Variety", "Size",
        "Packaging", "Net Wgt (kg)", "Price", "Currency", "Incoterms",
        "Moisture %", "FFA %", "Skin %"
    ]
    for i, col_name in enumerate(columns):
        worksheet.write(table_start_row, i, col_name, table_header_format)
        worksheet.set_column(i, i, 15)
    worksheet.set_column('B:B', 20)
    worksheet.set_column('C:C', 25)
    worksheet.set_column('D:D', 20)
    worksheet.set_column('F:F', 25)

    # ReferenceData Sheet
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

    # Data Validation
    for row in range(table_start_row + 1, 100):
        worksheet.data_validation(row, 0, {'validate': 'list', 'source': cat_range})
        worksheet.data_validation(row, 1, {'validate': 'list', 'source': group_range})
        worksheet.data_validation(row, 2, {'validate': 'list', 'source': type_range})
        worksheet.data_validation(row, 3, {'validate': 'list', 'source': var_range})
        worksheet.data_validation(row, 4, {'validate': 'list', 'source': size_range})
        worksheet.data_validation(row, 5, {'validate': 'list', 'source': pack_range})
        worksheet.data_validation(row, 8, {'validate': 'list', 'source': curr_range})
        worksheet.data_validation(row, 9, {'validate': 'list', 'source': inco_range})

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
        st.caption("Sadece Müşteriler eller Yeni Personel için")
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

    # ----------------------------------------------------------------
    # SCENARIO 1: FACTORY PORTAL (EMPLOYEE + ADMINISTRATOR)
    # ----------------------------------------------------------------
    if role in ['employee', 'administrator']:
        
        # 1. PERMISSION LOGIC
        if role == 'administrator':
            allowed_ids = [1, 2, 3, 4, 5, 6] # Added 6 for Admin
        else:
            allowed_ids = user.get('allowed_modules', [])
            if allowed_ids is None: allowed_ids = []
        
        # 2. GENERATE MENU
        available_menu_names = []
        for mod_id in sorted(allowed_ids):
            if mod_id in MODULE_MAP:
                available_menu_names.append(MODULE_MAP[mod_id])
        
        if not available_menu_names:
            st.error("🚫 Yetkili olduğunuz modül bulunmamaktadır.")
            st.stop()
            
        module = st.sidebar.radio("Fabrika Menüsü", available_menu_names)

        # ==========================
        # MODÜL 1: ŞUBE ÜRÜN GİRİŞİ
        # ==========================
        if module == MODULE_MAP[1]:
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

        # ==========================
        # MODÜL 2: FABRİKA ÜRÜN GİRİŞİ
        # ==========================
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
                    w_twin = r4c1.
