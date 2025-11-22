import streamlit as st
import pandas as pd
from db_utils import supabase, login_user, insert_record
import time

st.set_page_config(page_title="Fındık Fabrikası Yönetimi", layout="wide")

# --- YARDIMCI: RANDIMAN HESAPLAYICI ---
def calculate_randiman(sample_weight, good_kernel, shrivelled_kernel):
    # Formül: ((Sağlam İç + (Buruşuk / 2)) / Numune Ağırlığı) * 100
    if sample_weight == 0:
        return 0.0
    try:
        numerator = good_kernel + (shrivelled_kernel / 2)
        r = (numerator / sample_weight) * 100
        return r
    except:
        return 0.0

# --- YARDIMCI: EKSTRA ORAN HESAPLAYICI ---
def calculate_extra_rates(good, shriv, vis_rot, hid_rot, tumor):
    # Toplam İç Ağırlığı (Total Kernel Weight)
    total_kernel = good + shriv + vis_rot + hid_rot + tumor
    
    if total_kernel == 0:
        return 0.0, 0.0
    
    try:
        # Urlu Oranı (Tumor Rate)
        tumor_rate = (tumor / total_kernel) * 100
        
        # Buruşuk Oranı (Shrivelled Rate)
        shriv_rate = (shriv / total_kernel) * 100
        
        return tumor_rate, shriv_rate
    except:
        return 0.0, 0.0

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
        else:
            st.error("Giriş Başarısız. E-posta veya şifreyi kontrol edin.")

# --- ANA UYGULAMA ---
if not st.session_state.user:
    login_section()
else:
    # Kenar Çubuğu
    st.sidebar.info(f"Kullanıcı: {st.session_state.user.email}")
    if st.sidebar.button("Çıkış Yap"):
        st.session_state.user = None
        st.rerun()
        
    menu_options = ["1. Satın Alma", "2. Fabrika Ürün Girişi", "3. Yönetici Ayarları", "4. Stok Takibi"]
    module = st.sidebar.radio("Menü", menu_options)

    # ==========================
    # MODÜL 1: SATIN ALMA
    # ==========================
    if module == "1. Satın Alma":
        st.title("Modül 1: Satın Alma")
        
        hazelnut_group = ["Kabuklu Fındık", "İç Fındık", "İşlenmiş Fındık"]
        general_group = ["Malzeme", "Makine", "Hizmet"]
        all_options = hazelnut_group + general_group
        
        type_selector = st.selectbox("Satın Alma Kategorisi", all_options)
        
        # --- A. FINDIK ALIMI ---
        if type_selector in hazelnut_group:
            with st.form("hazelnut_form"):
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
                st.subheader("2. Kalite & Randıman")
                q1, q2, q3 = st.columns(3)
                sample_w = q1.number_input("Kabuklu Numune Ağırlığı (g)", value=250.0)
                good_k = q2.number_input("Sağlam İç (g)", value=0.0)
                shriv_k = q3.number_input("Buruşuk İç (g)", value=0.0)
                
                d1, d2, d3 = st.columns(3)
                vis_rot = d1.number_input("Görünen Çürük (g)", value=0.0)
                hid_rot = d2.number_input("Gizli Çürük (g)", value=0.0)
                tumor = d3.number_input("Ur (g)", value=0.0)

                s1, s2, s3 = st.columns(3)
                size_1 = s1.number_input("1. Numara (13 mm üzeri (%) )", value=0.0)
                under_size = s2.number_input("Elek Altı (9 mm altı (%) )", value=0.0)
                moisture = s3.number_input("Nem (%)", 0.0, 20.0, 5.0)
                
                # --- HESAPLAMA BUTONU VE GÖSTERGELER ---
                calc_pressed = st.form_submit_button("🔄 Analiz Sonuçlarını Hesapla")
                
                # Hesaplamalar
                randiman = calculate_randiman(sample_w, good_k, shriv_k)
                tumor_ratio, shriv_ratio = calculate_extra_rates(good_k, shriv_k, vis_rot, hid_rot, tumor)
                
                # Sonuçları Göster (3 Kolon)
                res1, res2, res3 = st.columns(3)
                res1.metric("Randıman", f"{randiman:.2f}%")
                res2.metric("Urlu Oranı", f"{tumor_ratio:.2f}%")
                res3.metric("Buruşuk Oranı", f"{shriv_ratio:.2f}%")

                st.markdown("---")
                st.subheader("3. Finansal Bilgiler")
                
                st.caption("Paketleme Detayları (Adet Giriniz)")
                p1, p2, p3 = st.columns(3)
                cnt_nylon = p1.number_input("Naylon Çuval Adedi", min_value=0, step=1)
                cnt_jute = p2.number_input("Jüt Çuval Adedi", min_value=0, step=1)
                cnt_bigbag = p3.number_input("Big Bag Adedi", min_value=0, step=1)

                st.caption("Ağırlık ve Fiyat")
                f1, f2 = st.columns(2)
                net_weight = f1.number_input("Toplam Net Ağırlık (kg)", min_value=0.0)
                doc_num = f2.text_input("Müstahsil Makbuzu / Fatura No")
                
                if reg_type == "Emanet":
                    st.info("İşlem Emanettir. Tutar 0 TL olarak kaydedilecek.")
                    gross_price = 0.0; net_price_50 = 0.0; unit_price = 0.0; total_val = 0.0; remaining = 0.0
                    pay_amount = 0.0; pay_method = "Yok"
                else:
                    gross_price = st.number_input("Borsa Fiyatı (50 Randıman)", value=120.0)
                    net_price_50 = gross_price / 1.0245
                    unit_price = net_price_50 * (randiman / 50.0)
                    total_val = unit_price * net_weight
                    st.write(f"**Net Fiyat (50 Rand):** {net_price_50:.2f} TL | **Gerçek Birim Fiyat:** {unit_price:.2f} TL")
                    st.info(f"**TOPLAM TUTAR:** {total_val:,.2f} TL")
                    
                    pay_col1, pay_col2 = st.columns(2)
                    pay_amount = pay_col1.number_input("Ödenen Tutar", value=0.0)
                    pay_method = pay_col2.selectbox("Ödeme Yöntemi", ["Nakit", "Banka Havalesi", "Çek"])
                    remaining = total_val - pay_amount
                    st.metric("Kalan Bakiye", f"{remaining:,.2f} TL")

                submit_save = st.form_submit_button("✅ Sözleşmeyi Kaydet")
                if submit_save:
                    payload = {
                        "created_by": st.session_state.user.email, "status": "Pending Arrival",
                        "category": type_selector, "supplier": supplier, "supplier_type": sup_type,
                        "id_number": id_num, "city": city_in, "district": dist_in, "village": vill_in,
                        "phone_number": contact, "cert_status": cert_status,
                        "reg_type": reg_type, "location": location, "item_type": hazelnut_type,
                        "sample_weight": sample_w, "good_kernel": good_k, "shrivelled_kernel": shriv_k,
                        "calculated_randiman": randiman, "visible_rotten": vis_rot, "hidden_rotten": hid_rot,
                        "tumorous": tumor, "size_1_percent": size_1, "undersize_percent": under_size, "moisture": moisture,
                        
                        "count_nylon": cnt_nylon, "count_jute": cnt_jute, "count_bigbag": cnt_bigbag,

                        "qty_ordered": net_weight, "document_number": doc_num, "gross_price_50": gross_price,
                        "net_price_50": net_price_50, "actual_unit_price": unit_price, "total_value": total_val,
                        "payment_amount": pay_amount, "payment_method": pay_method, "remaining_balance": remaining
                    }
                    try:
                        insert_record("purchases", payload)
                        st.success("Sözleşme Başarıyla Kaydedildi!")
                    except Exception as e: st.error(f"Hata: {e}")

        # --- B. MALZEME ALIMI ---
        elif type_selector == "Malzeme":
            st.subheader("Malzeme Seçimi")
            material_cats = ["Ambalaj Malzemeleri", "Bakım Malzemeleri", "Ofis Malzemeleri", "Temizlik Malzemeleri", "Eşantiyon & Hediye", "İş Kıyafetleri", "Gıda ve Mutfak", "Diğer"]
            
            c_cat, c_item = st.columns(2)
            selected_mat_cat = c_cat.selectbox("Kategori", material_cats)
            
            try:
                response = supabase.table("material_definitions").select("*").eq("category", selected_mat_cat).execute()
                items_data = response.data
                item_names = [row['item_name'] for row in items_data]
            except: items_data = []; item_names = []

            if item_names:
                selected_item_name = c_item.selectbox("Malzeme Seç", item_names)
                selected_item_data = next((item for item in items_data if item["item_name"] == selected_item_name), None)
                
                if selected_item_data:
                    with st.expander("ℹ️ Özellikleri Görüntüle", expanded=True):
                        sp1, sp2, sp3 = st.columns(3)
                        sp1.write(f"**Materyal:** {selected_item_data.get('mat_type', '-')}")
                        sp2.write(f"**Kullanım:** {selected_item_data.get('use_case', '-')}")
                        sp3.write(f"**Diğer:** {selected_item_data.get('other_specs', '-')}")
                        st.caption(f"Dış Ölçüler: {selected_item_data.get('dim_outer_l')} x {selected_item_data.get('dim_outer_w')} x {selected_item_data.get('dim_outer_d')} cm")
            else:
                c_item.warning("Bu kategoride tanımlı malzeme yok.")
                selected_item_name = c_item.text_input("Manuel Malzeme Adı")

            with st.form("material_form"):
                supplier = st.text_input("Tedarikçi")
                c3, c4
