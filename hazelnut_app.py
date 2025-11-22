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
def calculate_extra_rates(sample_weight, good, shriv, vis_rot, hid_rot, tumor, size1, undersize):
    total_kernel = good + shriv + vis_rot + hid_rot + tumor
    base_weight = total_kernel if total_kernel > 0 else 1
    
    try:
        tumor_rate = (tumor / base_weight) * 100
        shriv_rate = (shriv / base_weight) * 100
        vis_rot_rate = (vis_rot / base_weight) * 100
        hid_rot_rate = (hid_rot / base_weight) * 100
        
        # Boylama Oranları (Genellikle toplam iç ağırlığa göre)
        size1_rate = (size1 / base_weight) * 100
        undersize_rate = (undersize / base_weight) * 100
        
        return tumor_rate, shriv_rate, vis_rot_rate, hid_rot_rate, size1_rate, undersize_rate
    except:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

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
                st.subheader("2. Kalite, Miktar ve Fiyatlandırma")
                
                col_q1, col_q2 = st.columns([1, 1])
                
                with col_q1:
                    st.markdown("**Kalite Analizi (Eksper)**")
                    sample_w = st.number_input("Kabuklu Numune Ağırlığı (g)", value=250.0)
                    good_k = st.number_input("Sağlam İç (g)", value=0.0)
                    shriv_k = st.number_input("Buruşuk İç (g)", value=0.0)
                    vis_rot = st.number_input("Görünen Çürük (g)", value=0.0)
                    hid_rot = st.number_input("Gizli Çürük (g)", value=0.0)
                    tumor = st.number_input("Ur (g)", value=0.0)
                    
                    s1, s2 = st.columns(2)
                    size_1_g = s1.number_input("1. Numara İç - 13 mm üzeri (g)", value=0.0)
                    undersize_g = s2.number_input("Elek Altı İç - 9 mm altı (g)", value=0.0)
                    moisture = st.number_input("Nem (%)", 0.0, 20.0, 5.0)

                with col_q2:
                    st.markdown("**Miktar ve Paketleme**")
                    net_weight = st.number_input("Toplam Net Ağırlık (kg)", min_value=0.0)
                    
                    st.caption("Paket Adetleri")
                    p1, p2, p3 = st.columns(3)
                    cnt_nylon = p1.number_input("Naylon", min_value=0)
                    cnt_jute = p2.number_input("Jüt", min_value=0)
                    cnt_bigbag = p3.number_input("Big Bag", min_value=0)
                    
                    st.markdown("---")
                    st.markdown("**Fiyatlandırma**")
                    
                    if reg_type == "Emanet":
                        st.info("Emanet Alım: Fiyat 0 TL")
                        gross_price = 0.0
                    else:
                        gross_price = st.number_input("Borsa Fiyatı (50 Randıman)", value=120.0)

                st.markdown("---")
                calc_pressed = st.form_submit_button("🔄 Hesapla (Randıman & Fiyat)")
                
                randiman = calculate_randiman(sample_w, good_k, shriv_k)
                tumor_r, shriv_r, vis_rot_r, hid_rot_r, size1_r, under_r = calculate_extra_rates(
                    sample_w, good_k, shriv_k, vis_rot, hid_rot, tumor, size_1_g, undersize_g
                )
                
                net_price_50 = gross_price / 1.0245
                unit_price = net_price_50 * (randiman / 50.0)
                total_val = unit_price * net_weight

                if calc_pressed or True: 
                    k1, k2, k3 = st.columns(3)
                    k1.metric("Randıman", f"%{randiman:.2f}")
                    k2.metric("13mm+ Oranı", f"%{size1_r:.2f}")
                    k3.metric("Elek Altı Oranı", f"%{under_r:.2f}")
                    
                    k4, k5, k6, k7 = st.columns(4)
                    k4.metric("Buruşuk", f"%{shriv_r:.2f}")
                    k5.metric("Urlu", f"%{tumor_r:.2f}")
                    k6.metric("G. Çürük", f"%{vis_rot_r:.2f}")
                    k7.metric("Gizli Çürük", f"%{hid_rot_r:.2f}")
                    
                    if reg_type != "Emanet":
                        st.success(f"💰 **TOPLAM TUTAR:** {total_val:,.2f} TL")
                        f1, f2 = st.columns(2)
                        f1.write(f"**Net Baz Fiyat (50R):** {net_price_50:.2f} TL")
                        f2.write(f"**Randımanlı Birim Fiyat:** {unit_price:.2f} TL")

                st.markdown("---")
                st.subheader("3. Finansal Bilgiler (Ödeme)")
                
                f1, f2, f3 = st.columns(3)
                doc_num = f1.text_input("Müstahsil Makbuzu No")
                pay_amount = f2.number_input("Yapılan Ödeme Tutar", value=0.0)
                pay_method = f3.selectbox("Ödeme Yöntemi", ["Nakit", "Banka Havalesi", "Çek"])
                
                remaining = total_val - pay_amount
                if reg_type != "Emanet":
                    st.metric("Kalan Bakiye", f"{remaining:,.2f} TL")

                submit_save = st.form_submit_button("✅ Kaydet ve Bitir")
                
                if submit_save:
                    payload = {
                        "created_by": st.session_state.user.email, "status": "Pending Arrival",
                        "category": type_selector, "supplier": supplier, "supplier_type": sup_type,
                        "id_number": id_num, "city": city, "district": dist_in, "village": vill_in,
                        "phone_number": contact, "cert_status": cert_status,
                        "reg_type": reg_type, "location": location, "item_type": hazelnut_type,
                        "sample_weight": sample_w, "good_kernel": good_k, "shrivelled_kernel": shriv_k,
                        "calculated_randiman": randiman, "visible_rotten": vis_rot, "hidden_rotten": hid_rot,
                        "tumorous": tumor, 
                        "size_1_percent": size_1_g, "undersize_percent": undersize_g, 
                        "moisture": moisture,
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
                        # YENİ EKLENEN BİLGİLER
                        sp3.write(f"**Satış Birimi:** {selected_item_data.get('sales_unit', '-')} ({selected_item_data.get('unit_quantity', 1)} adet)")
                        
                        sp4, sp5 = st.columns(2)
                        sp4.write(f"**Notlar:** {selected_item_data.get('notes', '-')}")
                        # YENİ BOYUT FORMATI
                        sp5.caption(f"Dış Boyutlar: {selected_item_data.get('dim_outer', '-')}")
                        sp5.caption(f"Ağırlık: {selected_item_data.get('unit_weight_g', '-')} g")
            else:
                c_item.warning("Bu kategoride tanımlı malzeme yok.")
                selected_item_name = c_item.text_input("Manuel Malzeme Adı")

            with st.form("material_form"):
                supplier = st.text_input("Tedarikçi")
                c3, c4 = st.columns(2)
                qty = c3.number_input("Miktar (Sipariş Edilen Birim)", min_value=1.0, value=1.0)
                price = c4.number_input("Toplam Maliyet (TL)", min_value=0.0)
                
                if st.form_submit_button("✅ Siparişi Oluştur"):
                    payload = {
                        "category": "Malzeme", "supplier": supplier, "item_type": selected_item_name,
                        "item_sub_type": selected_mat_cat, "qty_ordered": qty, "total_value": price,
                        "status": "Pending Arrival", "created_by": st.session_state.user.email
                    }
                    insert_record("purchases", payload)
                    st.success("Sipariş Kaydedildi!")

        # --- C. GENEL (Makine, Hizmet) ---
        else:
            with st.form("general_form"):
                c1, c2 = st.columns(2)
                supplier = c1.text_input("Tedarikçi / Sağlayıcı")
                item_desc = c2.text_input("Açıklama / İsim")
                c3, c4 = st.columns(2)
                qty = c3.number_input("Miktar", 1.0)
                price = c4.number_input("Toplam Tutar", 0.0)
                
                if st.form_submit_button("✅ Siparişi Oluştur"):
                    payload = {"category": type_selector, "supplier": supplier, "item_type": item_desc, "qty_ordered": qty, "total_value": price, "status": "Pending Arrival", "created_by": st.session_state.user.email}
                    insert_record("purchases", payload)
                    st.success("Kaydedildi!")

    # ==========================
    # MODÜL 2: FABRİKA ÜRÜN GİRİŞİ
    # ==========================
    elif module == "2. Fabrika Ürün Girişi":
        st.title("Modül 2: Fabrika Ürün Girişi")
        try:
            response = supabase.table("purchases").select("*").eq("status", "Pending Arrival").execute()
            pending_df = pd.DataFrame(response.data)
            
            if not pending_df.empty:
                st.subheader("Beklenen Sevkiyatlar")
                st.dataframe(pending_df[["id", "supplier", "item_type", "qty_ordered", "location"]])
                
                st.markdown("---")
                po_ids = pending_df['id'].tolist()
                selected_id = st.selectbox("Kabul Edilecek Siparişi Seçin (ID)", po_ids)
                selected_row = pending_df[pending_df['id'] == selected_id].iloc[0]
                
                st.info(f"Kabul Ediliyor: **{selected_row['item_type']}** - {selected_row['supplier']}")
                
                with st.form("intake_confirm"):
                    c1, c2 = st.columns(2)
                    plate = c1.text_input("Araç Plakası")
                    waybill = c2.text_input("İrsaliye No")
                    received_qty = st.number_input("Kantar Net Ağırlık / Adet", value=float(selected_row['qty_ordered'] or 0))
                    loc_warehouse = st.text_input("Depo / Silo Konumu")
                    
                    if st.form_submit_button("Girişi Onayla"):
                        supabase.table("purchases").update({"status": "Received"}).eq("id", selected_id).execute()
                        
                        intake_payload = {
                            "po_id": int(selected_id), "plate_number": plate, "waybill_no": waybill,
                            "received_qty": received_qty, "variance": received_qty - float(selected_row['qty_ordered'] or 0),
                            "location_in_warehouse": loc_warehouse, "created_by": st.session_state.user.email
                        }
                        insert_record("intake_log", intake_payload)
                        
                        stock_payload = {
                            "item_name": selected_row['item_type'],
                            "category": selected_row.get('category', 'Unknown'),
                            "quantity": received_qty, 
                            "move_type": "Intake",
                            "location": loc_warehouse,
                            "created_by": st.session_state.user.email
                        }
                        insert_record("stock_movements", stock_payload)

                        st.success("Giriş Onaylandı ve Stoğa Eklendi!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.info("Bekleyen sevkiyat bulunamadı.")
        except Exception as e: st.error(f"Hata: {e}")

    # ==========================
    # MODÜL 3: YÖNETİCİ AYARLARI
    # ==========================
    elif module == "3. Yönetici Ayarları":
        st.title("🛠️ Yönetici Ayarları")
        tab1, tab2 = st.tabs(["Malzeme Tanımları", "Kullanıcı Yönetimi"])
        
        with tab1:
            st.subheader("Malzeme Tanımlarını Yönet")
            fixed_cats = ["Ambalaj Malzemeleri", "Bakım Malzemeleri", "Ofis Malzemeleri", "Temizlik Malzemeleri", "Eşantiyon & Hediye", "İş Kıyafetleri", "Gıda ve Mutfak", "Diğer"]
            
            unit_options = ['adet', 'gr', 'kg', 'bobin', 'rulo', 'paket', 'deste', 'palet', 'litre', 'mililitre', 'metreküp', 'desimetreküp', 'santimetreküp', 'metre', 'desimetre', 'santimetre', 'milimetre', 'bigbag', 'kamyon', 'tır', 'tank', 'metrekare', 'santimetrekare', 'ar', 'dekar', 'hektar']

            with st.expander("Veritabanı Listesini Görüntüle"):
                current = supabase.table("material_definitions").select("*").execute().data
                st.dataframe(pd.DataFrame(current), use_container_width=True)
            
            st.markdown("---")
            st.write("### ➕ Yeni Malzeme Ekle")
            with st.form("add_material_form"):
                c1, c2 = st.columns(2)
                new_cat = c1.selectbox("Kategori", fixed_cats)
                new_item = c2.text_input("Malzeme Adı")
                
                g1, g2, g3 = st.columns(3)
                use_case = g1.text_input("Kullanım Amacı"); mat_type = g2.text_input("Materyal (Plastik vb.)"); other_spec = g3.text_input("Diğer Özellikler")
                
                # --- YENİ EKLENEN ALANLAR ---
                u1, u2 = st.columns(2)
                sales_u = u1.selectbox("Satış Birimi", unit_options)
                unit_q = u2.number_input("Satış Birimindeki Adet/Miktar", value=1.0)
                notes_txt = st.text_area("Notlar")

                # --- GÜNCELLENEN BOYUT ALANLARI (TEXT) ---
                st.caption("Boyutlar ve Ağırlık")
                o1, o2, o3 = st.columns(3)
                dim_out_txt = o1.text_input("Dış Boyutlar (En x Boy x Yükseklik) mm")
                dim_in_txt = o2.text_input("İç Boyutlar (En x Boy x Yükseklik) mm")
                weight_g = o3.number_input("Ağırlık (gram)", 0.0)

                if st.form_submit_button("Tanımı Kaydet"):
                    if new_item:
                        payload = {
                            "category": new_cat, "item_name": new_item, 
                            "use_case": use_case, "mat_type": mat_type, "other_specs": other_spec, 
                            "sales_unit": sales_u, "unit_quantity": unit_q, "notes": notes_txt,
                            # YENİ ALANLAR
                            "dim_outer": dim_out_txt, 
                            "dim_inner": dim_in_txt, 
                            "unit_weight_g": weight_g
                        }
                        supabase.table("material_definitions").insert(payload).execute()
                        st.success("Eklendi!"); time.sleep(1); st.rerun()

            st.markdown("---")
            st.write("### ✏️ Düzenle (Modify)")
            m1, m2 = st.columns(2)
            mod_cat_filter = m1.selectbox("Kategori Filtrele", fixed_cats)
            mod_items = supabase.table("material_definitions").select("*").eq("category", mod_cat_filter).order('item_name').execute().data
            
            if mod_items:
                mod_names = [i['item_name'] for i in mod_items]
                target_name = m2.selectbox("Düzenlenecek Malzeme", mod_names)
                target_row = next(i for i in mod_items if i["item_name"] == target_name)
                
                with st.form("modify_form"):
                    st.info(f"Düzenleniyor: {target_name}")
                    c_new_name = st.text_input("İsim", value=target_row['item_name'])
                    
                    # Specs
                    mg1, mg2, mg3 = st.columns(3)
                    c_mat = mg1.text_input("Materyal", value=target_row.get('mat_type') or "")
                    c_use = mg2.text_input("Kullanım", value=target_row.get('use_case') or "")
                    c_spec = mg3.text_input("Diğer", value=target_row.get('other_specs') or "")
                    
                    # Units
                    mu1, mu2 = st.columns(2)
                    current_unit = target_row.get('sales_unit') if target_row.get('sales_unit') in unit_options else unit_options[0]
                    c_sales_u = mu1.selectbox("Satış Birimi", unit_options, index=unit_options.index(current_unit))
                    c_unit_q = mu2.number_input("Birim Adet", value=float(target_row.get('unit_quantity') or 1.0))
                    c_notes = st.text_area("Notlar", value=target_row.get('notes') or "")

                    # Dims (Updated to Text)
                    st.caption("Boyutlar ve Ağırlık")
                    mo1, mo2, mo3 = st.columns(3)
                    c_dim_out = mo1.text_input("Dış Boyutlar", value=target_row.get('dim_outer') or "")
                    c_dim_in = mo2.text_input("İç Boyutlar", value=target_row.get('dim_inner') or "")
                    c_weight = mo3.number_input("Ağırlık (g)", value=float(target_row.get('unit_weight_g') or 0.0))

                    if st.form_submit_button("Güncelle"):
                        update_payload = {
                            "item_name": c_new_name, "mat_type": c_mat, "use_case": c_use, "other_specs": c_spec,
                            "sales_unit": c_sales_u, "unit_quantity": c_unit_q, "notes": c_notes,
                            "dim_outer": c_dim_out, "dim_inner": c_dim_in, "unit_weight_g": c_weight
                        }
                        supabase.table("material_definitions").update(update_payload).eq("id", target_row['id']).execute()
                        st.success("Güncellendi!"); time.sleep(1); st.rerun()

            st.markdown("---")
            st.write("### 🗑️ Sil")
            d1, d2, d3 = st.columns([2, 2, 1])
            del_cat = d1.selectbox("Kategori Filtrele (Sil)", fixed_cats)
            del_items = supabase.table("material_definitions").select("*").eq("category", del_cat).execute().data
            
            if del_items:
                del_names = [i['item_name'] for i in del_items]
                del_target = d2.selectbox("Silinecek Malzeme", del_names)
                if d3.button("Sil"):
                    supabase.table("material_definitions").delete().eq("category", del_cat).eq("item_name", del_target).execute()
                    st.success("Silindi"); time.sleep(1); st.rerun()

    # ==========================
    # MODÜL 4: STOK TAKİBİ
    # ==========================
    elif module == "4. Stok Takibi":
        st.title("📦 Canlı Stok Durumu")
        
        moves = supabase.table("stock_movements").select("*").execute().data
        df_moves = pd.DataFrame(moves)
        
        if not df_moves.empty:
            inventory_summary = df_moves.groupby('item_name')['quantity'].sum().reset_index()
            inventory_summary.columns = ['Malzeme / Ürün', 'Mevcut Stok']
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader("Mevcut Stok Seviyeleri")
                st.dataframe(inventory_summary, use_container_width=True)
            
            with col2:
                st.metric("Takip Edilen Kalem", len(inventory_summary))
                st.metric("Toplam Hareket", len(df_moves))

            st.markdown("---")
            st.subheader("📜 Hareket Geçmişi")
            
            filter_item = st.selectbox("Ürün Filtrele", ["Tümü"] + list(df_moves['item_name'].unique()))
            
            if filter_item != "Tümü":
                display_df = df_moves[df_moves['item_name'] == filter_item]
            else:
                display_df = df_moves
                
            st.dataframe(display_df.sort_values(by='created_at', ascending=False), use_container_width=True)
            
        else:
            st.info("Henüz stok hareketi yok. Fabrika Ürün Girişi modülünden giriş yapınız.")
