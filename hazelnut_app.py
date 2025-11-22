import streamlit as st
import pandas as pd
from db_utils import supabase, login_user, insert_record
import time

st.set_page_config(page_title="Fındık Fabrikası Yönetimi", layout="wide")

# --- YARDIMCI: ORAN HESAPLAYICI (YENİ DETAYLI) ---
def calculate_detailed_rates(base_weight, inputs):
    """
    base_weight: İç Numune Ağırlığı (g)
    inputs: Dictionary of {label: weight_g}
    Returns: Dictionary of {label: percentage}
    """
    results = {}
    if base_weight == 0:
        return {k: 0.0 for k in inputs}
    
    for key, val in inputs.items():
        # Count based items (Adet/Tane) cannot be calculated as % by weight easily
        # unless we assume a weight. For now we return 0.0 or raw value for counts if needed.
        if "adet" in key or "tane" in key:
             results[key] = 0.0 
        else:
            results[key] = (val / base_weight) * 100
    return results

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
        
        # TABS FOR MAIN CATEGORIES
        tab_findik, tab_malzeme, tab_genel = st.tabs(["🌰 Fındık Alımı", "📦 Malzeme Alımı", "⚙️ Makine & Hizmet"])
        
        # --- TAB 1: FINDIK ALIMI ---
        with tab_findik:
            hazelnut_cat = st.selectbox("Fındık Kategorisi", ["Kabuklu Fındık", "İç Fındık", "İşlenmiş Fındık"])
            
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
                
                # ============================================================
                # YENİ BÖLÜM 2: KABUKLU FINDIK İÇİN DETAYLI ANALİZ
                # ============================================================
                if hazelnut_cat == "Kabuklu Fındık":
                    st.subheader("2. Detaylı Kalite Analizi (Laboratuvar)")
                    
                    # 1. TEMEL & KİMYASAL
                    st.markdown("##### A. Temel & Kimyasal Analiz")
                    k1, k2, k3, k4 = st.columns(4)
                    sample_weight = k1.number_input("İç Numune Ağırlığı (g)", value=100.0)
                    moisture = k2.number_input("Nem (%)", 0.0, 100.0, 5.0)
                    ffa = k3.number_input("FFA (%)", 0.0, 100.0, 0.0)
                    peroxide = k4.number_input("Peroksit (meqO2/kg)", 0.0)

                    # 2. FİZİKSEL KUSURLAR
                    st.markdown("##### B. Fiziksel Kusurlar (Gram)")
                    
                    # Row 1
                    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
                    good_k = r1c1.number_input("Sağlam İç (g)", 0.0)
                    vis_rot = r1c2.number_input("Görünen Çürük (g)", 0.0)
                    hid_rot = r1c3.number_input("Gizli Çürük (g)", 0.0)
                    worm = r1c4.number_input("Kurt Yenikli (g)", 0.0)
                    
                    # Row 2
                    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
                    vis_mold = r2c1.number_input("Görünen Küflü (g)", 0.0)
                    hid_mold = r2c2.number_input("Gizli Küflü (g)", 0.0)
                    vis_tumor = r2c3.number_input("Görünen Urlu (g)", 0.0)
                    hid_tumor = r2c4.number_input("Gizli Urlu (g)", 0.0)

                    # Row 3
                    r3c1, r3c2, r3c3, r3c4 = st.columns(4)
                    shriv = r3c1.number_input("Buruşuk İç (g)", 0.0)
                    lemon = r3c2.number_input("Limoni (g)", 0.0)
                    decayed = r3c3.number_input("Vurgun (g)", 0.0)
                    broken = r3c4.number_input("Kırık (g)", 0.0)

                    # Row 4
                    r4c1, r4c2, r4c3, r4c4 = st.columns(4)
                    twin = r4c1.number_input("İkiz (g)", 0.0)
                    other_type = r4c2.number_input("Diğer Tipler (g)", 0.0)
                    undersize = r4c3.number_input("Elek Altı (g)", 0.0)
                    oversize = r4c4.number_input("Elek Üstü (g)", 0.0)

                    # 3. DİĞER & MİKROBİYOLOJİK
                    st.markdown("##### C. Yabancı Madde & Mikrobiyolojik")
                    m1, m2, m3, m4 = st.columns(4)
                    membrane = m1.number_input("Zar Atmayan Tane (adet)", 0)
                    shell_g = m2.number_input("Kabuk (g)", 0.0)
                    foreign_cnt = m3.number_input("Yabancı Madde (tane)", 0)
                    
                    m_row2_1, m_row2_2, m_row2_3, m_row2_4 = st.columns(4)
                    salmonella = m_row2_1.text_input("Salmonella (cfu/g)")
                    ecoli = m_row2_2.text_input("E. Coli (cfu/g)")
                    afla_b1 = m_row2_3.number_input("Aflatoksin B1 (ppb)", 0.0)
                    afla_tot = m_row2_4.number_input("Aflatoksin Total (ppb)", 0.0)

                    # --- HESAPLAMA & SONUÇLAR ---
                    st.markdown("---")
                    calc_btn = st.form_submit_button("🔄 Oranları Hesapla")
                    
                    # Oransal Hesaplamalar
                    # Not: Adet olanları oranlayamayız, gram olanları oranlarız.
                    calc_inputs = {
                        "Sağlam İç": good_k, "Görünen Çürük": vis_rot, "Gizli Çürük": hid_rot,
                        "Görünen Küflü": vis_mold, "Gizli Küflü": hid_mold,
                        "Görünen Urlu": vis_tumor, "Gizli Urlu": hid_tumor,
                        "Kurt Yenikli": worm, "Buruşuk İç": shriv, "Limoni": lemon,
                        "Vurgun": decayed, "Kırık": broken, "İkiz": twin,
                        "Diğer Tipler": other_type, "Elek Altı": undersize, "Elek Üstü": oversize,
                        "Kabuk": shell_g
                    }
                    
                    calculated_pcts = calculate_detailed_rates(sample_weight, calc_inputs)
                    
                    if calc_btn or True:
                        st.markdown("##### Analiz Sonuçları (%)")
                        
                        # Sonuçları güzel bir Grid içinde gösterelim
                        res_cols = st.columns(6)
                        idx = 0
                        for label, pct in calculated_pcts.items():
                            with res_cols[idx % 6]:
                                st.metric(label, f"%{pct:.2f}")
                            idx += 1
                        
                        # Adet bazlılar (Manuel gösterim)
                        with res_cols[idx % 6]:
                            st.metric("Yabancı Madde", f"{foreign_cnt} tane")
                        with res_cols[(idx+1) % 6]:
                            st.metric("Zar Atmayan", f"{membrane} adet")

                # ============================================================
                # İÇ FINDIK / İŞLENMİŞ (BASİT FORM - ESKİ HALİ)
                # ============================================================
                else:
                    st.warning("Bu fındık türü için detaylı analiz henüz tanımlanmadı. Standart form gösteriliyor.")
                    # Eski basit inputları buraya koyabilirsiniz veya boş bırakabilirsiniz.
                    # Şimdilik fiyat hesaplaması için basit bir ağırlık alalım
                    sample_weight = 0
                    good_k = 0
                    moisture = st.number_input("Nem (%)", 0.0)

                # ------------------------------------------------
                # 3. FİNANSAL BİLGİLER (ORTAK)
                # ------------------------------------------------
                st.markdown("---")
                st.subheader("3. Miktar ve Finansal Bilgiler")
                
                c_qty, c_price = st.columns(2)
                
                with c_qty:
                    st.caption("Miktar ve Paketleme")
                    net_weight = st.number_input("Toplam Net Ağırlık (kg)", min_value=0.0)
                    
                    cp1, cp2, cp3 = st.columns(3)
                    cnt_nylon = cp1.number_input("Naylon", min_value=0)
                    cnt_jute = cp2.number_input("Jüt", min_value=0)
                    cnt_bigbag = cp3.number_input("Big Bag", min_value=0)

                with c_price:
                    st.caption("Fiyatlandırma")
                    if reg_type == "Emanet":
                        st.info("Emanet Alım")
                        final_price = 0.0
                    else:
                        # Detaylı analizde Randıman hesabı (Sample/Inshell) olmadığı için
                        # Kullanıcıdan direkt fiyatı istiyoruz.
                        final_price = st.number_input("Anlaşılan Toplam Tutar (TL)", min_value=0.0)
                        if net_weight > 0:
                            st.caption(f"Birim Fiyat: {final_price/net_weight:.2f} TL/kg")

                st.markdown("---")
                st.subheader("Ödeme Bilgileri")
                f1, f2, f3 = st.columns(3)
                doc_num = f1.text_input("Makbuz / Fatura No")
                pay_amount = f2.number_input("Ödenen Tutar", 0.0)
                pay_method = f3.selectbox("Ödeme Yöntemi", ["Nakit", "Banka", "Çek"])
                
                if reg_type != "Emanet":
                    st.metric("Kalan Bakiye", f"{final_price - pay_amount:,.2f} TL")

                submit_save = st.form_submit_button("✅ Kaydet")
                
                if submit_save:
                    # Veritabanı kaydı
                    payload = {
                        "created_by": st.session_state.user.email, "status": "Pending Arrival",
                        "category": hazelnut_cat, "supplier": supplier, "supplier_type": sup_type,
                        "id_number": id_num, "city": city, "district": dist_in, "village": vill_in,
                        "phone_number": contact, "cert_status": cert_status,
                        "reg_type": reg_type, "location": location, "item_type": hazelnut_type,
                        "qty_ordered": net_weight, "total_value": final_price, "document_number": doc_num,
                        "payment_amount": pay_amount, "remaining_balance": final_price - pay_amount,
                        "count_nylon": cnt_nylon, "count_jute": cnt_jute, "count_bigbag": cnt_bigbag,
                        
                        # YENİ DETAYLI ANALİZ VERİLERİ
                        "analysis_inner_weight": sample_weight,
                        "moisture": moisture,
                        "analysis_ffa": ffa, "analysis_peroxide": peroxide,
                        "analysis_visible_mold": vis_mold, "analysis_hidden_mold": hid_mold,
                        "analysis_visible_tumor": vis_tumor, "analysis_hidden_tumor": hid_tumor,
                        "analysis_worm_eaten": worm, "analysis_lemon": lemon, "analysis_decayed": decayed,
                        "analysis_broken": broken, "analysis_twin": twin, "analysis_other_types": other_type,
                        "analysis_oversize": oversize, "analysis_shell": shell_g, 
                        "analysis_membrane_adhered": membrane, "analysis_foreign_matter": foreign_cnt,
                        "analysis_salmonella": salmonella, "analysis_ecoli": ecoli,
                        "analysis_afla_b1": afla_b1, "analysis_afla_total": afla_tot,
                        
                        # Eski kolonlara uyumluluk (Rapolarda patlamaması için)
                        "good_kernel": good_k, "visible_rotten": vis_rot, "hidden_rotten": hid_rot,
                        "shrivelled_kernel": shriv, "undersize_percent": undersize # Gram olarak kaydeder
                    }
                    
                    try:
                        insert_record("purchases", payload)
                        st.success("Başarıyla Kaydedildi!")
                    except Exception as e: st.error(f"Hata: {e}")

        # --- TAB 2: MALZEME ALIMI ---
        with tab_malzeme:
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
                    with st.expander("ℹ️ Özellikler", expanded=True):
                        sp1, sp2, sp3 = st.columns(3)
                        sp1.write(f"**Materyal:** {selected_item_data.get('mat_type', '-')}")
                        sp2.write(f"**Birim:** {selected_item_data.get('sales_unit', '-')} ({selected_item_data.get('unit_quantity', 1)})")
                        sp3.caption(f"Notlar: {selected_item_data.get('notes', '-')}")
            else:
                c_item.warning("Tanımlı malzeme yok.")
                selected_item_name = c_item.text_input("Manuel Giriş")

            with st.form("material_purchase_form"):
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
            general_type = st.selectbox("Tür", ["Makine", "Hizmet"])
            with st.form("gen_form"):
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
    # MODÜL 2: FABRİKA GİRİŞİ
    # ==========================
    elif module == "2. Fabrika Ürün Girişi":
        st.title("Modül 2: Fabrika Ürün Girişi")
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
    # MODÜL 3: YÖNETİCİ
    # ==========================
    elif module == "3. Yönetici Ayarları":
        st.title("🛠️ Yönetici Ayarları")
        tab1, tab2 = st.tabs(["Malzeme Tanımları", "Kullanıcılar"])
        with tab1:
            cats = ["Ambalaj Malzemeleri", "Bakım Malzemeleri", "Ofis Malzemeleri", "Temizlik Malzemeleri", "Eşantiyon & Hediye", "İş Kıyafetleri", "Gıda ve Mutfak", "Diğer"]
            units = ['adet', 'gr', 'kg', 'bobin', 'rulo', 'paket', 'palet', 'litre', 'metre', 'bigbag']
            
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
                    
                    if st.form_submit_button("Kaydet"):
                        insert_record("material_definitions", {"category": cat, "item_name": name, "sales_unit": unit, "unit_quantity": uq})
                        st.success("Eklendi!")
            
            elif action == "Düzenle":
                sel_cat = st.selectbox("Kategori", cats)
                items = supabase.table("material_definitions").select("*").eq("category", sel_cat).execute().data
                if items:
                    target = st.selectbox("Malzeme", [i['item_name'] for i in items])
                    row = next(i for i in items if i['item_name'] == target)
                    with st.form("edit"):
                        new_name = st.text_input("Ad", row['item_name'])
                        if st.form_submit_button("Güncelle"):
                            supabase.table("material_definitions").update({"item_name": new_name}).eq("id", row['id']).execute()
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
    # MODÜL 4: STOK
    # ==========================
    elif module == "4. Stok Takibi":
        st.title("📦 Stok")
        moves = supabase.table("stock_movements").select("*").execute().data
        df = pd.DataFrame(moves)
        if not df.empty:
            stock = df.groupby('item_name')['quantity'].sum().reset_index()
            st.dataframe(stock, use_container_width=True)
            st.markdown("---")
            st.dataframe(df.sort_values(by='created_at', ascending=False))
        else: st.info("Hareket yok.")
