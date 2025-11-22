import streamlit as st
import pandas as pd
from db_utils import supabase, login_user, insert_record
import time

st.set_page_config(page_title="Hazelnut Factory Manager", layout="wide")

# --- HELPER: RANDIMAN CALCULATOR ---
def calculate_randiman(sample_weight, good_kernel, shrivelled_kernel):
    # Formula: ((Good Kernel + (Shrivelled / 2)) / Sample Weight) * 100
    if sample_weight == 0:
        return 0.0
    try:
        numerator = good_kernel + (shrivelled_kernel / 2)
        r = (numerator / sample_weight) * 100
        return r
    except:
        return 0.0

# --- LOGIN SYSTEM ---
if 'user' not in st.session_state:
    st.session_state.user = None

def login_section():
    st.title("🌰 Hazelnut Factory Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Log In"):
        user = login_user(email, password)
        if user:
            st.session_state.user = user
            st.success("Login Successful!")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("Login Failed. Check email/password.")

# --- MAIN APP ---
if not st.session_state.user:
    login_section()
else:
    # Sidebar
    st.sidebar.info(f"User: {st.session_state.user.email}")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
        
    menu_options = ["1. Purchase (Satın Alma)", "2. Intake (Mal Kabul)", "3. Admin Settings", "4. Inventory"]
    module = st.sidebar.radio("Navigate", menu_options)

    # ==========================
    # MODULE 1: PURCHASE
    # ==========================
    if module == "1. Purchase (Satın Alma)":
        st.title("Module 1: Purchasing Hub")
        
        hazelnut_group = ["Inshell Hazelnuts (Kabuklu Findik)", "Hazelnut Kernels (Ic Findik)", "Processed Hazelnuts (Islenmis Findik)"]
        general_group = ["Materials", "Machines", "Services"]
        all_options = hazelnut_group + general_group
        
        type_selector = st.selectbox("Purchase Category", all_options)
        
        # --- A. HAZELNUT LOGIC ---
        if type_selector in hazelnut_group:
            with st.form("hazelnut_form"):
                st.subheader("1. Supplier & Origin")
                c1, c2, c3 = st.columns(3)
                supplier = c1.text_input("Supplier Name")
                sup_type = c2.selectbox("Supplier Type", ["Farmer", "Merchant", "Company"])
                id_num = c3.text_input("ID Number (TCKN/VKN)")
                
                c4, c5, c6 = st.columns(3)
                city = c4.text_input("City/Village")
                contact = c5.text_input("Phone Number")
                cert_status = c6.selectbox("Certification", ["None", "Organic", "Rainforest Alliance", "Avella"])

                c7, c8, c9 = st.columns(3)
                reg_type = c7.selectbox("Registration Type", ["Purchased", "Loaned (Emanet)"])
                location = c8.selectbox("Place of Registration", ["Factory", "Field", "Store"])
                hazelnut_type = c9.selectbox("Hazelnut Variety", ["Karışık", "Giresun Tombul", "Çakıldak", "Kara", "Sivri", "Palaz", "Badem", "Foşa", "Yomra"])
                
                st.markdown("---")
                st.subheader("2. Quality & Randıman")
                q1, q2, q3 = st.columns(3)
                sample_w = q1.number_input("Sample Inshell Size (g)", value=250.0)
                good_k = q2.number_input("Good Kernel (g)", value=0.0)
                shriv_k = q3.number_input("Shrivelled Kernel (g)", value=0.0)
                
                d1, d2, d3 = st.columns(3)
                vis_rot = d1.number_input("Visible Rotten (g)", value=0.0)
                hid_rot = d2.number_input("Hidden Rotten (g)", value=0.0)
                tumor = d3.number_input("Tumorous (g)", value=0.0)

                s1, s2, s3 = st.columns(3)
                size_1 = s1.number_input("Size 1 %>13mm (%)", value=0.0)
                under_size = s2.number_input("Undersize %<9mm (%)", value=0.0)
                moisture = s3.number_input("Moisture (%)", 0.0, 20.0, 5.0)
                
                calc_pressed = st.form_submit_button("🔄 Calculate Yield & Stats")
                randiman = calculate_randiman(sample_w, good_k, shriv_k)
                st.metric("Calculated Randıman", f"{randiman:.2f}%")

                st.markdown("---")
                st.subheader("3. Financials")
                f1, f2 = st.columns(2)
                net_weight = f1.number_input("Total Net Weight (kg)", min_value=0.0)
                doc_num = f2.text_input("Document Number")
                
                if reg_type == "Loaned (Emanet)":
                    st.info("Transaction is Emanet. Value is 0 TL.")
                    gross_price = 0.0; net_price_50 = 0.0; unit_price = 0.0; total_val = 0.0; remaining = 0.0
                    pay_amount = 0.0; pay_method = "None"
                else:
                    gross_price = st.number_input("Gross Price (50 Rand)", value=120.0)
                    net_price_50 = gross_price / 1.0245
                    unit_price = net_price_50 * (randiman / 50.0)
                    total_val = unit_price * net_weight
                    st.write(f"**Net Price:** {net_price_50:.2f} TL | **Actual Unit Price:** {unit_price:.2f} TL")
                    st.info(f"**TOTAL VALUE:** {total_val:,.2f} TL")
                    
                    pay_col1, pay_col2 = st.columns(2)
                    pay_amount = pay_col1.number_input("Payment Amount", value=0.0)
                    pay_method = pay_col2.selectbox("Way of Payment", ["Cash", "Bank Transfer", "Check"])
                    remaining = total_val - pay_amount
                    st.metric("Remaining Balance", f"{remaining:,.2f} TL")

                submit_save = st.form_submit_button("✅ Create Contract & Save")
                if submit_save:
                    payload = {
                        "created_by": st.session_state.user.email, "status": "Pending Arrival",
                        "category": type_selector, "supplier": supplier, "supplier_type": sup_type,
                        "id_number": id_num, "city": city, "phone_number": contact, "cert_status": cert_status,
                        "reg_type": reg_type, "location": location, "item_type": hazelnut_type,
                        "sample_weight": sample_w, "good_kernel": good_k, "shrivelled_kernel": shriv_k,
                        "calculated_randiman": randiman, "visible_rotten": vis_rot, "hidden_rotten": hid_rot,
                        "tumorous": tumor, "size_1_percent": size_1, "undersize_percent": under_size, "moisture": moisture,
                        "qty_ordered": net_weight, "document_number": doc_num, "gross_price_50": gross_price,
                        "net_price_50": net_price_50, "actual_unit_price": unit_price, "total_value": total_val,
                        "payment_amount": pay_amount, "payment_method": pay_method, "remaining_balance": remaining
                    }
                    try:
                        insert_record("purchases", payload)
                        st.success("Contract Saved!")
                    except Exception as e: st.error(f"Error: {e}")

        # --- B. MATERIALS LOGIC ---
        elif type_selector == "Materials":
            st.subheader("Material Selection")
            material_cats = ["Packaging Materials", "Maintenance Materials", "Office Materials", "Cleaning Materials", "Give Aways", "Clothes and Textile", "Food & Kitchen", "Other"]
            
            c_cat, c_item = st.columns(2)
            selected_mat_cat = c_cat.selectbox("Category", material_cats)
            
            try:
                response = supabase.table("material_definitions").select("*").eq("category", selected_mat_cat).execute()
                items_data = response.data
                item_names = [row['item_name'] for row in items_data]
            except: items_data = []; item_names = []

            if item_names:
                selected_item_name = c_item.selectbox("Select Item", item_names)
                selected_item_data = next((item for item in items_data if item["item_name"] == selected_item_name), None)
                
                if selected_item_data:
                    with st.expander("ℹ️ View Item Specs", expanded=True):
                        sp1, sp2, sp3 = st.columns(3)
                        sp1.write(f"**Material:** {selected_item_data.get('mat_type', '-')}")
                        sp2.write(f"**Use:** {selected_item_data.get('use_case', '-')}")
                        sp3.write(f"**Other:** {selected_item_data.get('other_specs', '-')}")
                        st.caption(f"Outer: {selected_item_data.get('dim_outer_l')} x {selected_item_data.get('dim_outer_w')} x {selected_item_data.get('dim_outer_d')} cm")
            else:
                c_item.warning("No items defined.")
                selected_item_name = c_item.text_input("Manual Item Name")

            with st.form("material_form"):
                supplier = st.text_input("Supplier")
                c3, c4 = st.columns(2)
                qty = c3.number_input("Quantity", min_value=1.0, value=1.0)
                price = c4.number_input("Total Cost", min_value=0.0)
                
                if st.form_submit_button("✅ Create Order"):
                    payload = {
                        "category": "Materials", "supplier": supplier, "item_type": selected_item_name,
                        "item_sub_type": selected_mat_cat, "qty_ordered": qty, "total_value": price,
                        "status": "Pending Arrival", "created_by": st.session_state.user.email
                    }
                    insert_record("purchases", payload)
                    st.success("Order Saved!")

        # --- C. GENERAL LOGIC ---
        else:
            with st.form("general_form"):
                c1, c2 = st.columns(2)
                supplier = c1.text_input("Supplier")
                item_desc = c2.text_input("Item Name")
                c3, c4 = st.columns(2)
                qty = c3.number_input("Quantity", 1.0)
                price = c4.number_input("Cost", 0.0)
                
                if st.form_submit_button("✅ Create Order"):
                    payload = {"category": type_selector, "supplier": supplier, "item_type": item_desc, "qty_ordered": qty, "total_value": price, "status": "Pending Arrival", "created_by": st.session_state.user.email}
                    insert_record("purchases", payload)
                    st.success("Saved!")

    # ==========================
    # MODULE 2: INTAKE
    # ==========================
    elif module == "2. Intake (Mal Kabul)":
        st.title("Module 2: Factory Gate Intake")
        try:
            response = supabase.table("purchases").select("*").eq("status", "Pending Arrival").execute()
            pending_df = pd.DataFrame(response.data)
            
            if not pending_df.empty:
                st.subheader("Expected Arrivals")
                st.dataframe(pending_df[["id", "supplier", "item_type", "qty_ordered", "location"]])
                
                st.markdown("---")
                po_ids = pending_df['id'].tolist()
                selected_id = st.selectbox("Select Purchase ID to Receive", po_ids)
                selected_row = pending_df[pending_df['id'] == selected_id].iloc[0]
                
                st.info(f"Receiving: **{selected_row['item_type']}** from {selected_row['supplier']}")
                
                with st.form("intake_confirm"):
                    c1, c2 = st.columns(2)
                    plate = c1.text_input("Plate Number")
                    waybill = c2.text_input("Waybill No")
                    received_qty = st.number_input("Actual Received Quantity", value=float(selected_row['qty_ordered'] or 0))
                    loc_warehouse = st.text_input("Warehouse Location")
                    
                    if st.form_submit_button("Confirm Arrival"):
                        # 1. Mark Purchase as Received
                        supabase.table("purchases").update({"status": "Received"}).eq("id", selected_id).execute()
                        
                        # 2. Save Receipt Log
                        intake_payload = {
                            "po_id": int(selected_id), "plate_number": plate, "waybill_no": waybill,
                            "received_qty": received_qty, "variance": received_qty - float(selected_row['qty_ordered'] or 0),
                            "location_in_warehouse": loc_warehouse, "created_by": st.session_state.user.email
                        }
                        insert_record("intake_log", intake_payload)
                        
                        # 3. UPDATE INVENTORY (STOCK MOVEMENTS)
                        stock_payload = {
                            "item_name": selected_row['item_type'],
                            "category": selected_row.get('category', 'Unknown'),
                            "quantity": received_qty, # Positive = Add to Stock
                            "move_type": "Intake",
                            "location": loc_warehouse,
                            "created_by": st.session_state.user.email
                        }
                        insert_record("stock_movements", stock_payload)

                        st.success("Arrival Confirmed & Added to Inventory!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.info("No pending shipments found.")
        except Exception as e: st.error(f"Error: {e}")

    # ==========================
    # MODULE 3: ADMIN SETTINGS
    # ==========================
    elif module == "3. Admin Settings":
        st.title("🛠️ Admin Settings")
        tab1, tab2 = st.tabs(["Manage Materials", "User Management"])
        
        with tab1:
            st.subheader("Manage Material Definitions")
            fixed_cats = ["Packaging Materials", "Maintenance Materials", "Office Materials", "Cleaning Materials", "Give Aways", "Clothes and Textile", "Food & Kitchen", "Other"]

            with st.expander("View Full Database List"):
                current = supabase.table("material_definitions").select("*").execute().data
                st.dataframe(pd.DataFrame(current), use_container_width=True)
            
            st.markdown("---")
            st.write("### ➕ Add New Item")
            with st.form("add_material_form"):
                c1, c2 = st.columns(2)
                new_cat = c1.selectbox("Category", fixed_cats)
                new_item = c2.text_input("Item Name")
                
                g1, g2, g3 = st.columns(3)
                use_case = g1.text_input("Use"); mat_type = g2.text_input("Material"); other_spec = g3.text_input("Specs")
                
                o1, o2, o3 = st.columns(3)
                out_l = o1.number_input("Outer L", 0.0); out_w = o2.number_input("Outer W", 0.0); out_d = o3.number_input("Outer D", 0.0)
                
                i1, i2, i3 = st.columns(3)
                inn_l = i1.number_input("Inner L", 0.0); inn_w = i2.number_input("Inner W", 0.0); inn_d = i3.number_input("Inner D", 0.0)

                if st.form_submit_button("Save Definition"):
                    if new_item:
                        payload = {"category": new_cat, "item_name": new_item, "use_case": use_case, "mat_type": mat_type, "other_specs": other_spec, "dim_outer_l": out_l, "dim_outer_w": out_w, "dim_outer_d": out_d, "dim_inner_l": inn_l, "dim_inner_w": inn_w, "dim_inner_d": inn_d}
                        supabase.table("material_definitions").insert(payload).execute()
                        st.success("Added!"); time.sleep(1); st.rerun()

            st.markdown("---")
            st.write("### ✏️ Modify Item")
            m1, m2 = st.columns(2)
            mod_cat_filter = m1.selectbox("Filter Category (Modify)", fixed_cats)
            mod_items = supabase.table("material_definitions").select("*").eq("category", mod_cat_filter).order('item_name').execute().data
            
            if mod_items:
                mod_names = [i['item_name'] for i in mod_items]
                target_name = m2.selectbox("Select Item", mod_names)
                target_row = next(i for i in mod_items if i["item_name"] == target_name)
                
                with st.form("modify_form"):
                    c_new_name = st.text_input("Name", value=target_row['item_name'])
                    c_mat = st.text_input("Material", value=target_row.get('mat_type', ''))
                    if st.form_submit_button("Update"):
                        supabase.table("material_definitions").update({"item_name": c_new_name, "mat_type": c_mat}).eq("id", target_row['id']).execute()
                        st.success("Updated!"); time.sleep(1); st.rerun()

            st.markdown("---")
            st.write("### 🗑️ Delete Item")
            d1, d2, d3 = st.columns([2, 2, 1])
            del_cat = d1.selectbox("Filter Category (Delete)", fixed_cats)
            del_items = supabase.table("material_definitions").select("*").eq("category", del_cat).execute().data
            
            if del_items:
                del_names = [i['item_name'] for i in del_items]
                del_target = d2.selectbox("Item to Delete", del_names)
                if d3.button("Delete"):
                    supabase.table("material_definitions").delete().eq("category", del_cat).eq("item_name", del_target).execute()
                    st.success("Deleted"); time.sleep(1); st.rerun()

    # ==========================
    # MODULE 4: INVENTORY
    # ==========================
    elif module == "4. Inventory":
        st.title("📦 Live Inventory")
        
        # 1. Fetch all movements
        moves = supabase.table("stock_movements").select("*").execute().data
        df_moves = pd.DataFrame(moves)
        
        if not df_moves.empty:
            # 2. Calculate Current Stock
            # Group by Item Name and Sum the Quantity column
            inventory_summary = df_moves.groupby('item_name')['quantity'].sum().reset_index()
            inventory_summary.columns = ['Item Name', 'Current Stock']
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader("Current Stock Levels")
                st.dataframe(inventory_summary, use_container_width=True)
            
            with col2:
                st.metric("Total Items Tracked", len(inventory_summary))
                st.metric("Total Transactions", len(df_moves))

            st.markdown("---")
            st.subheader("📜 Movement History (Audit Trail)")
            
            # Filter History
            filter_item = st.selectbox("Filter History by Item", ["All"] + list(df_moves['item_name'].unique()))
            
            if filter_item != "All":
                display_df = df_moves[df_moves['item_name'] == filter_item]
            else:
                display_df = df_moves
                
            st.dataframe(display_df.sort_values(by='created_at', ascending=False), use_container_width=True)
            
        else:
            st.info("No inventory movements recorded yet. Go to Intake (Module 2) to receive goods.")
