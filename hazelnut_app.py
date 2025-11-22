import streamlit as st
import pandas as pd
from db_utils import supabase, login_user, insert_record
import time

st.set_page_config(page_title="Fındık Fabrikası Yönetimi", layout="wide")

# --- YARDIMCI: HESAPLAYICILAR ---
def calculate_randiman(sample_w, good, shriv):
    if sample_w == 0: return 0.0
    return ((good + (shriv / 2)) / sample_w) * 100

def calculate_percentages(base_w, inputs):
    results = {}
    if base_w == 0: return {k: 0.0 for k in inputs}
    for k, v in inputs.items():
        results[k] = (v / base_w) * 100
    return results

def calculate_detailed_rates(base_weight, inputs):
    results = {}
    if base_weight == 0: return {k: 0.0 for k in inputs}
    for key, val in inputs.items():
        if "adet" in key or "tane" in key: results[key] = val 
        else: results[key] = (val / base_weight) * 100
    return results

# --- LISTS ---
CALIBRE_OPTIONS = [
    "Mixed Size", "21mm+", "20mm+", "19mm+", "18mm+", "17mm+", "16mm+", 
    "15-16mm", "14-15mm", "13-15mm", "13-14mm", "12-14mm", "12-13mm", 
    "11-13mm", "11-12mm", "10-12mm", "10-11mm", "9-11mm", "9-10mm", 
    "9mm-", "9mm+", "0-2mm", "1-3mm", "2-4mm", "4-6mm", "5-7mm", 
    "6-8mm", "7-11mm", "3-11mm", "5-11mm", "15μ", "18μ", "20μ", 
    "21μ", "22μ", "23μ", "24μ", "25μ", "26μ", "27μ", "28μ", "29μ", 
    "30μ", "31μ", "32μ", "33μ", "34μ", "35μ"
]

# --- GİRİŞ SİSTEMİ ---
if 'user' not in st.session_state:
    st.session_state.user = None

def login_section():
    st.title("🌰 Fındık Fabrikası Giriş")
    email = st.text_input("E-posta")
    password = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap"):
        user = login_user(email, password)
        if user:
            st.session_state.user = user
            st.success("Giriş Başarılı!")
            time.sleep(0.5)
            st.rerun()
        else: st.error("Giriş Başarısız.")

# --- ANA UYGULAMA ---
if not st.session_state.user:
    login_section()
else:
    st.sidebar.info(f"Kullanıcı: {st.session_state.user.email}")
    if st.sidebar.button("Çıkış Yap"):
        st.session_state.user = None
        st.rerun()
        
    menu_options = [
        "1. Şube Ürün Girişi", 
        "2. Fabrika Ürün Girişi", 
        "3. Mal Kabul (Kantar)", 
        "4. Yönetici Ayarları", 
        "5. Stok Takibi"
    ]
    module = st.sidebar.radio("Menü", menu_options)

    # =========================================================
    # MODÜL 1: ŞUBE ÜRÜN GİRİŞİ (SADECE KABUKLU FINDIK)
    # =========================================================
    if module == "1. Şube Ürün Girişi":
        st.title("Modül 1: Şube Ürün Girişi")
        
        # KATEGORİ SEÇİMİ KALDIRILDI - SABİT KABUKLU
        hazelnut_cat = "Kabuklu Fındık"
        st.info("Bu modül Şubelerden yapılan **Kabuklu Fındık** alımları içindir.")
        
        with st.form("sube_hazelnut_form"):
            st.subheader("1. Müstahsil & Tedarikçi")
            c1, c2, c3 = st.columns(3)
            supplier = c1.text_input("Tedarikçi Adı")
            sup_type = c2.selectbox("Tedarikçi Tipi", ["Müstahsil", "Tüccar", "Şirket"])
            id_num = c3.text_input("TCKN / VKN")
            
            c4, c5, c6 = st.columns(3)
            city = c4.text_input("İl")
            dist_in = c5.text_input("İlçe")
            vill_in = c6.text_input("Köy / Mahalle")

            c_cont, c_cert = st.columns(2)
            contact = c_cont.text_input("Telefon No")
            cert_status = c_cert.selectbox("Sertifikasyon", ["Yok", "Organik", "Rainforest Alliance", "Avella"])

            st.markdown("---")
            c7, c8, c9 = st.columns(3)
            reg_type = c7.selectbox("Alım Şekli", ["Satın Alma", "Emanet"])
            location = c8.selectbox("Teslimat Yeri", ["Fabrika", "Tarla", "Avella Şube"])
            hazelnut_type = c9.selectbox("Fındık Çeşidi", ["Karışık", "Giresun Tombul", "Çakıldak", "Kara", "Sivri", "Palaz", "Badem", "Foşa", "Yomra"])
            
            st.markdown("---")
            
            # DEĞİŞKENLER
            price_gross=0.0; price_net_deducted=0.0; val_randiman=0.0

            # KABUKLU FORM (STANDART)
            st.subheader("2. Kalite, Miktar ve Fiyatlandırma")
            col_q1, col_q2 = st.columns([1, 1])
            with col_q1:
                st.markdown("**Fiziksel Analiz (Eksper)**")
                w_sample = st.number_input("Kabuklu Numune Ağırlığı (g)", value=250.0)
                
                def show_percent(val, base):
                    if base > 0: return f"%{(val/base)*100:.2f}"
                    return "%0.00"

                w_good = st.number_input("Sağlam İç (g)", 0.0)
                w_shriv = st.number_input("Buruşuk İç (g)", 0.0)
                w_vis_rot = st.number_input("Görünen Çürük (g)", 0.0)
                w_hid_rot = st.number_input("Gizli Çürük (g)", 0.0)
                w_tumor = st.number_input("Ur (g)", 0.0)
                
                temp_total_inner = w_good + w_shriv + w_vis_rot + w_hid_rot + w_tumor
                base_calc = temp_total_inner if temp_total_inner > 0 else 1
                if temp_total_inner > 0:
                    st.caption(f"📊 Anlık Oranlar: Buruşuk: {show_percent(w_shriv, base_calc)} | G.Çürük: {show_percent(w_vis_rot, base_calc)} | Gizli Çürük: {show_percent(w_hid_rot, base_calc)} | Ur: {show_percent(w_tumor, base_calc)}")

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
            pcts = calculate_percentages(base_calc, {"Buruşuk": w_shriv, "Ur": w_tumor, "Görünen Çürük": w_vis_rot, "Gizli Çürük": w_hid_rot, "13mm+": w_over, "Elek Altı": w_under})
            
            net_price_50 = price_gross / 1.0245
            unit_price = net_price_50 * (val_randiman / 50.0)
            total_val = unit_price * net_weight
            
            if calc_pressed:
                st.markdown("##### Analiz Sonuçları")
                k1, k2, k3 = st.columns(3)
                k1.metric("Randıman", f"%{val_randiman:.2f}")
                k2.metric("13mm+ Oranı", f"%{pcts['13mm+']:.2f}")
                k3.metric("Elek Altı Oranı", f"%{pcts['Elek Altı']:.2f}")
                k4, k5, k6, k7 = st.columns(4)
                k4.metric("Buruşuk", f"%{pcts['Buruşuk']:.2f}")
                k5.metric("Urlu", f"%{pcts['Ur']:.2f}")
                k6.metric("G. Çürük", f"%{pcts.get('Görünen Çürük', 0):.2f}")
                k7.metric("Gizli Çürük", f"%{pcts.get('Gizli Çürük', 0):.2f}")
                
                if reg_type != "Emanet":
                    st.success(f"💰 **TOPLAM TUTAR:** {total_val:,.2f} TL")
                    st.caption(f"Birim Fiyat: {unit_price:.2f} TL")

            st.markdown("---")
            st.subheader("3. Ödeme ve Kayıt")
            f1, f2, f3 = st.columns(3)
            doc_num = f1.text_input("Makbuz / Fatura No")
            pay_amount = f2.number_input("Ödenen Tutar", 0.0)
            pay_method = f3.selectbox("Ödeme Yöntemi", ["Nakit", "Banka", "Çek"])
            if reg_type != "Emanet": st.metric("Kalan Bakiye", f"{total_val - pay_amount:,.2f} TL")

            if st.form_submit_button("✅ Şube Girişini Kaydet"):
                payload = {
                    "created_by": st.session_state.user.email, "status": "Pending Arrival",
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
                    "moisture": val_moist,
                    "calculated_randiman": val_randiman,
                    "gross_price_50": price_gross, "net_price_50": net_price_50, "actual_unit_price": unit_price
                }
                insert_record("purchases", payload)
                st.success("Şube Girişi Kaydedildi!")


    # ==========================
    # MODÜL 2: FABRİKA ÜRÜN GİRİŞİ (ESKİ MODÜL 1)
    # ==========================
    if module == "2. Fabrika Ürün Girişi":
        st.title("Modül 2: Fabrika Ürün Girişi")
        tab_findik, tab_malzeme, tab_genel = st.tabs(["🌰 Fındık Alımı", "📦 Malzeme Alımı", "⚙️ Makine & Hizmet"])
        
        # --- TAB 1: FINDIK (MODÜL 1 İLE AYNI FORM YAPISI) ---
        with tab_findik:
            hazelnut_cat = st.selectbox("Fındık Kategorisi", ["Kabuklu Fındık", "İç Fındık", "İşlenmiş Fındık"], key="fab_findik_cat")
            
            with st.form("fab_hazelnut_form"):
                st.subheader("1. Müstahsil & Tedarikçi")
                c1, c2, c3 = st.columns(3)
                supplier = c1.text_input("Tedarikçi Adı")
                sup_type = c2.selectbox("Tedarikçi Tipi", ["Müstahsil", "Tüccar", "Şirket"])
                id_num = c3.text_input("TCKN / VKN")
                
                c4, c5, c6 = st.columns(3)
                city = c4.text_input("İl")
                dist_in = c5.text_input("İlçe")
                vill_in = c6.text_input("Köy / Mahalle")

                c_cont, c_cert = st.columns(2)
                contact = c_cont.text_input("Telefon No")
                cert_status = c_cert.selectbox("Sertifikasyon", ["Yok", "Organik", "Rainforest Alliance", "Avella"])

                st.markdown("---")
                c7, c8, c9 = st.columns(3)
                reg_type = c7.selectbox("Alım Şekli", ["Satın Alma", "Emanet"])
                location = c8.selectbox("Teslimat Yeri", ["Fabrika", "Tarla", "Avella Şube"])
                hazelnut_type = c9.selectbox("Fındık Çeşidi", ["Karışık", "Giresun Tombul", "Çakıldak", "Kara", "Sivri", "Palaz", "Badem", "Foşa", "Yomra"])
                
                st.markdown("---")
                # --- ORTAK DEĞİŞKENLER (SCOPE SORUNUNU ÖNLEMEK İÇİN TEKRAR TANIMLA) ---
                w_sample=0.0; w_good=0.0; w_shriv=0.0; w_vis_rot=0.0; w_hid_rot=0.0; w_tumor=0.0
                w_under=0.0; w_over=0.0; val_moist=0.0; w_vis_mold=0.0; w_hid_mold=0.0; w_vis_tumor=0.0
                w_hid_tumor=0.0; w_worm=0.0; w_lemon=0.0; w_decayed=0.0; w_broken=0.0; w_twin=0.0
                w_other=0.0; w_shell=0.0; c_membrane=0; c_foreign=0
                l_ffa=0.0; l_perox=0.0; l_salm=""; l_ecoli=""; l_b1=0.0; l_tot=0.0; lab_cal=None
                price_gross=0.0; price_net_deducted=0.0; val_randiman=0.0

                if hazelnut_cat == "Kabuklu Fındık":
                    st.subheader("2. Kalite, Miktar ve Fiyatlandırma")
                    col_q1, col_q2 = st.columns([1, 1])
                    with col_q1:
                        st.markdown("**Fiziksel Analiz (Eksper)**")
                        w_sample = st.number_input("Kabuklu Numune Ağırlığı (g)", value=250.0)
                        def show_percent(val, base):
                            if base > 0: return f"%{(val/base)*100:.2f}"
                            return "%0.00"
                        w_good = st.number_input("Sağlam İç (g)", 0.0)
                        w_shriv = st.number_input("Buruşuk İç (g)", 0.0)
                        w_vis_rot = st.number_input("Görünen Çürük (g)", 0.0)
                        w_hid_rot = st.number_input("Gizli Çürük (g)", 0.0)
                        w_tumor = st.number_input("Ur (g)", 0.0)
                        temp_total_inner = w_good + w_shriv + w_vis_rot + w_hid_rot + w_tumor
                        base_calc = temp_total_inner if temp_total_inner > 0 else 1
                        if temp_total_inner > 0:
                            st.caption(f"📊 Anlık Oranlar: Buruşuk: {show_percent(w_shriv, base_calc)} | G.Çürük: {show_percent(w_vis_rot, base_calc)} | Gizli Çürük: {show_percent(w_hid_rot, base_calc)} | Ur: {show_percent(w_tumor, base_calc)}")
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
                    pcts = calculate_percentages(base_calc, {"Buruşuk": w_shriv, "Ur": w_tumor, "Görünen Çürük": w_vis_rot, "Gizli Çürük": w_hid_rot, "13mm+": w_over, "Elek Altı": w_under})
                    net_price_50 = price_gross / 1.0245
                    unit_price = net_price_50 * (val_randiman / 50.0)
                    total_val = unit_price * net_weight
                    if calc_pressed:
                        st.markdown("##### Analiz Sonuçları")
                        k1, k2, k3 = st.columns(3)
                        k1.metric("Randıman", f"%{val_randiman:.2f}")
                        k2.metric("13mm+ Oranı", f"%{pcts['13mm+']:.2f}")
                        k3.metric("Elek Altı Oranı", f"%{pcts['Elek Altı']:.2f}")
                        k4, k5, k6, k7 = st.columns(4)
                        k4.metric("Buruşuk", f"%{pcts['Buruşuk']:.2f}")
                        k5.metric("Urlu", f"%{pcts['Ur']:.2f}")
                        k6.metric("G. Çürük", f"%{pcts.get('Görünen Çürük', 0):.2f}")
                        k7.metric("Gizli Çürük", f"%{pcts.get('Gizli Çürük', 0):.2f}")
                        if reg_type != "Emanet":
                            st.success(f"💰 **TOPLAM TUTAR:** {total_val:,.2f} TL")
                            st.caption(f"Birim Fiyat: {unit_price:.2f} TL")
                else:
                    st.subheader("2. Detaylı Kalite Analizi (Laboratuvar)")
                    st.markdown("##### A. Temel & Kimyasal Analiz")
                    k1, k2, k3 = st.columns(3)
                    w_sample = k1.number_input("İç Numune Ağırlığı (g)", value=100.0)
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
                    m_row2_1, m_row2_2, m_row2_3, m_row2_4 = st.columns(4)
                    l_salm = m_row2_1.text_input("Salmonella")
                    l_ecoli = m_row2_2.text_input("E. Coli")
                    l_b1 = m_row2_3.number_input("Aflatoksin B1 (ppb)", 0.0)
                    l_tot = m_row2_4.number_input("Aflatoksin Total (ppb)", 0.0)
                    
                    st.markdown("---")
                    calc_btn = st.form_submit_button("📊 Rapor Oluştur")
                    if calc_btn:
                        st.info("📊 **Canlı Analiz Raporu**")
                        calc_inputs = {"Sağlam İç": w_good, "Görünen Çürük": w_vis_rot, "Gizli Çürük": w_hid_rot, "Görünen Küflü": w_vis_mold, "Gizli Küflü": w_hid_mold, "Görünen Urlu": w_vis_tumor, "Gizli Urlu": w_hid_tumor, "Kurt Yenikli": w_worm, "Buruşuk İç": w_shriv, "Limoni": w_lemon, "Vurgun": w_decayed, "Kırık": w_broken, "İkiz": w_twin, "Diğer Tipler": w_other, "Elek Altı": w_under, "Elek Üstü": w_over, "Kabuk": w_shell}
                        report_data = []
                        if w_sample > 0:
                            for k, v in calc_inputs.items():
                                pct = (v / w_sample) * 100
                                if v > 0: report_data.append({"Parametre": k, "Girdi (g)": f"{v} g", "Sonuç": f"%{pct:.2f}"})
                            if val_moist > 0: report_data.append({"Parametre": "Nem", "Girdi (g)": "-", "Sonuç": f"%{val_moist}"})
                            if l_ffa > 0: report_data.append({"Parametre": "FFA", "Girdi (g)": "-", "Sonuç": f"%{l_ffa}"})
                            if l_perox > 0: report_data.append({"Parametre": "Peroksit", "Girdi (g)": "-", "Sonuç": f"{l_perox} meq"})
                            if l_b1 > 0: report_data.append({"Parametre": "Aflatoksin B1", "Girdi (g)": "-", "Sonuç": f"{l_b1} ppb"})
                            if l_tot > 0: report_data.append({"Parametre": "Aflatoksin Total", "Girdi (g)": "-", "Sonuç": f"{l_tot} ppb"})
                            if l_salm: report_data.append({"Parametre": "Salmonella", "Girdi (g)": "-", "Sonuç": l_salm})
                            if l_ecoli: report_data.append({"Parametre": "E. Coli", "Girdi (g)": "-", "Sonuç": l_ecoli})
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
                    if reg_type == "Emanet": total_val = 0.0
                    else:
                        with cq2:
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
                    # KAYIT LOGİĞİ BURAYA (Modül 1 ile aynı, kopyala/yapıştır)
                    # Önemli: insert_record fonksiyonu çağrılırken tüm parametreler gönderilmeli.
                    payload = {
                        "created_by": st.session_state.user.email, "status": "Pending Arrival",
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
                        "moisture": val_moist,
                        "weight_visible_mold": w_vis_mold, "weight_hidden_mold": w_hid_mold,
                        "weight_visible_tumor": w_vis_tumor, "weight_hidden_tumor": w_hid_tumor,
                        "weight_worm_eaten": w_worm, "weight_lemon": w_lemon, "weight_decayed": w_decayed,
                        "weight_broken": w_broken, "weight_twin": w_twin, "weight_other": w_other, 
                        "weight_shell": w_shell, "count_membrane": c_membrane, "count_foreign": c_foreign,
                        "lab_ffa": l_ffa, "lab_peroxide": l_perox, "lab_calibre": lab_cal,
                        "lab_salmonella": l_salm, "lab_ecoli": l_ecoli, "lab_afla_b1": l_b1, "lab_afla_total": l_tot,
                        "calculated_randiman": val_randiman
                    }
                    if hazelnut_cat == "Kabuklu Fındık": payload.update({"gross_price_50": price_gross, "net_price_50": net_price_50, "actual_unit_price": unit_price})
                    else: payload.update({"actual_unit_price": price_net_deducted, "gross_price_50": price_gross})
                    
                    insert_record("purchases", payload)
                    st.success("Fabrika Girişi Kaydedildi!")

        # --- TAB 2: MALZEME ALIMI ---
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
                    payload = {"category": "Malzeme", "supplier": supplier, "item_type": selected_item_name, "item_sub_type": selected_mat_cat, "qty_ordered": qty, "total_value": price, "status": "Pending Arrival", "created_by": st.session_state.user.email}
                    insert_record("purchases", payload)
                    st.success("Kaydedildi!")

        # --- TAB 3: GENEL ---
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
                    insert_record("purchases", {"category": general_type, "supplier": supplier, "item_type": desc, "qty_ordered": qty, "total_value": price, "status": "Pending Arrival", "created_by": st.session_state.user.email})
                    st.success("Kaydedildi!")

    # ==========================
    # MODÜL 3: MAL KABUL
    # ==========================
    elif module == "3. Mal Kabul (Kantar)":
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
                        insert_record("intake_log", {"po_id": int(selected_id), "plate_number": plate, "waybill_no": waybill, "received_qty": qty, "location_in_warehouse": loc, "created_by": st.session_state.user.email})
                        insert_record("stock_movements", {"item_name": row['item_type'], "category": row.get('category'), "quantity": qty, "move_type": "Intake", "location": loc, "created_by": st.session_state.user.email})
                        st.success("Giriş Yapıldı!"); time.sleep(1); st.rerun()
            else: st.info("Bekleyen yok.")
        except Exception as e: st.error(f"Hata: {e}")

    # ==========================
    # MODÜL 4: YÖNETİCİ
    # ==========================
    elif module == "4. Yönetici Ayarları":
        st.title("🛠️ Yönetici Ayarları")
        tab1, tab2 = st.tabs(["Malzeme Tanımları", "Kullanıcılar"])
        with tab1:
            cats = ["Ambalaj Malzemeleri", "Bakım Malzemeleri", "Ofis Malzemeleri", "Temizlik Malzemeleri", "Eşantiyon & Hediye", "İş Kıyafetleri", "Gıda ve Mutfak", "Diğer"]
            units = ['adet', 'gr', 'kg', 'bobin', 'rulo', 'paket', 'deste', 'palet', 'litre', 'mililitre', 'metreküp', 'desimetreküp', 'santimetreküp', 'metre', 'desimetre', 'santimetre', 'milimetre', 'bigbag', 'kamyon', 'tır', 'tank', 'metrekare', 'santimetrekare', 'ar', 'dekar', 'hektar']
            with st.expander("Listeyi Gör"):
                data = supabase.table("material_definitions").select("*").execute().data
                st.dataframe(pd.DataFrame(data), use_container_width=True)
            st.markdown("---")
            st.write("### ➕ Ekle / ✏️ Düzenle / 🗑️ Sil")
            action = st.radio("İşlem", ["Ekle", "Düzenle", "Sil"], horizontal=True)
            if action == "Ekle":
                with st.form("add"):
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
                    with st.form("edit"):
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

    # ==========================
    # MODÜL 5: STOK
    # ==========================
    elif module == "5. Stok Takibi":
        st.title("📦 Stok")
        moves = supabase.table("stock_movements").select("*").execute().data
        df = pd.DataFrame(moves)
        if not df.empty:
            stock = df.groupby('item_name')['quantity'].sum().reset_index()
            st.dataframe(stock, use_container_width=True)
            st.markdown("---")
            st.dataframe(df.sort_values(by='created_at', ascending=False))
        else: st.info("Hareket yok.")
