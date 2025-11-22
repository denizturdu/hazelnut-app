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
    # Sidebar Navigation
    st.sidebar.info(f"User: {st.session_state.user.email}")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
        
    module = st.sidebar.radio("Navigate", ["1. Purchase (Satın Alma)", "2. Intake (Mal Kabul)", "3. Admin Settings"])

    # ==========================
    # MODULE 1: PURCHASE
    # ==========================
    if module == "1. Purchase (Satın Alma)":
        st.title("Module 1: Purchasing Hub")
        
        # Define Category Groups
        hazelnut_group = [
            "Inshell Hazelnuts (Kabuklu Findik)", 
            "Hazelnut Kernels (Ic Findik)", 
            "Processed Hazelnuts (Islenmis Findik)"
        ]
        
        general_group = [
            "Materials", 
            "Machines", 
            "Services"
        ]
        
        all_options = hazelnut_group + general_group
        type_selector = st.selectbox("Purchase Category", all_options)
        
        # --- A. HAZELNUT LOGIC (Detailed Form) ---
        if type_selector in hazelnut_group:
            with st.form("hazelnut_form"):
                st.subheader("1. Supplier & Origin (Kimlik)")
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
                hazelnut_type = c9.selectbox("Hazelnut Variety", [
                    "Karışık", "Giresun Tombul", "Çakıldak", "Kara", 
                    "Sivri", "Palaz", "Badem", "Foşa", "Yomra"
                ])
                
                st.markdown("---")
                st.subheader("2. Quality & Randıman (Eksper)")
                
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
                st.subheader("3. Financials (Finans)")
                
                f1, f2 = st.columns(2)
                net_weight = f1.number_input("Total Net Weight (kg)", min_value=0.0)
                doc_num = f2.text_input("Document Number (Müstahsil Makbuzu No)")
                
                # Financial Logic
                if reg_type == "Loaned (Emanet)":
                    st.info("Transaction is Emanet. Value is 0 TL.")
                    gross_price = 0.0
                    net_price_50 = 0.0
                    unit_price = 0.0
                    total_val = 0.0
                    remaining = 0.0
                    pay_amount = 0.0
                    pay_method = "None"
                else:
                    gross_price = st.number_input("Gross Price (50 Rand)", value=120.0)
                    net_price_50 = gross_price / 1.0245
                    unit_price = net_price_50 * (randiman / 50.0)
                    total_val = unit_price * net_weight
                    
                    st.write(f"**Net Price (50 Rand):** {net_price_50:.2f} TL")
                    st.write(f"**Actual Price (per kg):** {unit_price:.2f} TL")
                    st.info(f"**TOTAL VALUE:** {total_val:,.2f} TL")

                    pay_col1, pay_col2 = st.columns(2)
                    pay_amount = pay_col1.number_input("Payment Amount (TL)", value=0.0)
                    pay_method = pay_col2.selectbox("Way of Payment", ["Cash", "Bank Transfer", "Check"])
                    remaining = total_val - pay_amount
                    st.metric("Remaining Balance", f"{remaining:,.2f} TL")

                submit_save = st.form_submit_button("✅ Create Contract & Save")
                
                if submit_save:
                    payload = {
                        "created_by": st.session_state.user.email,
                        "status": "Pending Arrival",
                        "category": type_selector,
                        "supplier": supplier,
                        "supplier_type": sup_type,
                        "id_number": id_num,
                        "city": city,
                        "phone_number": contact,
                        "cert_status": cert_status,
                        "reg_type": reg_type,
                        "location": location,
                        "item_type": hazelnut_type,
                        "sample_weight": sample_w,
                        "good_kernel": good_k,
                        "shrivelled_kernel": shriv_k,
                        "calculated_randiman": randiman,
                        "visible_rotten": vis_rot,
                        "hidden_rotten": hid_rot,
                        "tumorous": tumor,
                        "size_1_percent": size_1,
                        "undersize_percent": under_size,
                        "moisture": moisture,
                        "qty_ordered": net_weight,
                        "document_number": doc_num,
                        "gross_price_50": gross_price,
                        "net_price_50": net_price_50,
                        "actual_unit_price": unit_price,
                        "total_value": total_val,
                        "payment_amount": pay_amount,
                        "payment_method": pay_method,
                        "remaining_balance": remaining
                    }
                    try:
                        insert_record("purchases", payload)
                        st.success("Contract Saved Successfully!")
                    except Exception as e:
                        st.error(f"Error saving: {e}")

        # --- B. MATERIALS LOGIC (Fetch from DB + Display Specs) ---
        elif type_selector == "Materials":
            st.subheader(f"Purchase Order: {type_selector}")
            
            material_cats = [
                "Packaging Materials", "Maintenance Materials", "Office Materials",
                "Cleaning Materials", "Give Aways", "Clothes and Textile",
                "Food & Kitchen", "Other"
            ]
            
            st.subheader("Material Selection")
            
            # 1. Select Category & Item OUTSIDE form
            c_cat, c_item = st.columns(2)
            selected_mat_cat = c_cat.selectbox("Category", material_cats)
            
            try:
                # Fetch FULL details
                response = supabase.table("material_definitions").select("*").eq("category", selected_mat_cat).execute()
                items_data = response.data
                item_names = [row['item_name'] for row in items_data]
            except:
                items_data = []
                item_names = []

            if item_names:
                selected_item_name = c_item.selectbox("Select Item", item_names)
                
                # Find the specific row data
                selected_item_data = next((item for item in items_data if item["item_name"] == selected_item_name), None)
                
                # --- DISPLAY SPECS (Read Only) ---
                if selected_item_data:
                    with st.expander("ℹ️ View Item Specs", expanded=True):
                        sp1, sp2, sp3 = st.columns(3)
                        sp1.write(f"**Material:** {selected_item_data.get('mat_type', '-')}")
                        sp2.write(f"**Use:** {selected_item_data.get('use_case', '-')}")
                        sp3.write(f"**Other:** {selected_item_data.get('other_specs', '-')}")
                        
                        st.caption("Outer Dims (cm)")
                        st.write(f"{selected_item_data.get('dim_outer_l')} x {selected_item_data.get('dim_outer_w')} x {selected_item_data.get('dim_outer_d')}")

            else:
                c_item.warning("No items defined in this category.")
                selected_item_name = c_item.text_input("Manual Item Name")

            # 2. Purchase Details INSIDE form
            with st.form("material_form"):
                supplier = st.text_input("Supplier")
                c3, c4 = st.columns(2)
                qty = c3.number_input("Quantity", min_value=1.0, value=1.0)
                price = c4.number_input("Total Cost (TL)", min_value=0.0)
                
                submit_mat = st.form_submit_button("✅ Create Order")
                
                if submit_mat:
                    payload = {
                        "category": "Materials",
                        "supplier": supplier,
                        "item_type": selected_item_name,
                        "item_sub_type": selected_mat_cat,
                        "qty_ordered": qty,
                        "total_value": price,
                        "status": "Pending Arrival",
                        "created_by": st.session_state.user.email
                    }
                    insert_record("purchases", payload)
                    st.success("Order Saved!")

        # --- C. GENERAL LOGIC (Machines & Services) ---
        else:
            st.subheader(f"Purchase Order: {type_selector}")
            with st.form("general_form"):
                c1, c2 = st.columns(2)
                supplier = c1.text_input("Supplier / Provider")
                item_desc = c2.text_input("Description / Item Name")
                c3, c4 = st.columns(2)
                qty = c3.number_input("Quantity", min_value=1.0, value=1.0)
                price = c4.number_input("Total Estimated Cost (TL)", min_value=0.0)
                
                submit_gen = st.form_submit_button(f"✅ Create {type_selector} Order")
                if submit_gen:
                    payload = {
                        "category": type_selector,
                        "supplier": supplier,
                        "item_type": item_desc,
                        "qty_ordered": qty,
                        "total_value": price,
                        "status": "Pending Arrival",
                        "created_by": st.session_state.user.email
                    }
                    insert_record("purchases", payload)
                    st.success(f"{type_selector} Order Saved!")

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
                st.subheader("Process Arrival")
                
                po_ids = pending_df['id'].tolist()
                selected_id = st.selectbox("Select Purchase ID", po_ids)
                selected_row = pending_df[pending_df['id'] == selected_id].iloc[0]
                
                st.info(f"Receiving: {selected_row['item_type']} from {selected_row['supplier']}")
                
                with st.form("intake_confirm"):
                    c1, c2 = st.columns(2)
                    plate = c1.text_input("Plate Number")
                    waybill = c2.text_input("Waybill No")
                    
                    received_qty = st.number_input("Actual Received Quantity", value=float(selected_row['qty_ordered'] or 0))
                    loc_warehouse = st.text_input("Warehouse Location")
                    
if st.form_submit_button("Confirm Arrival"):
                        # 1. Update Purchase Status
                        supabase.table("purchases").update({"status": "Received"}).eq("id", selected_id).execute()
                        
                        # 2. Insert into Intake Log (The Receipt)
                        intake_payload = {
                            "po_id": int(selected_id),
                            "received_qty": received_qty,
                            "item_name": selected_row['item_type'], # Save item name for reference
                            "created_by": st.session_state.user.email
                        }
                        insert_record("intake_log", intake_payload)

                        # 3. INSERT INTO STOCK MOVEMENTS (The Inventory Increase)
                        stock_payload = {
                            "item_name": selected_row['item_type'],
                            "category": selected_row.get('category', 'Unknown'),
                            "quantity": received_qty,  # Positive Number = Stock INCREASE
                            "move_type": "Intake",
                            "location": loc_warehouse,
                            "created_by": st.session_state.user.email
                        }
                        insert_record("stock_movements", stock_payload)

                        st.success("Arrival Confirmed & Stock Increased!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.info("No pending shipments found.")
        except Exception as e:
            st.error(f"Error loading data: {e}")

   # ==========================
    # MODULE 3: ADMIN SETTINGS
    # ==========================
    elif module == "3. Admin Settings":
        st.title("🛠️ Admin Settings")
        
        tab1, tab2 = st.tabs(["Manage Materials", "User Management"])
        
        with tab1:
            st.subheader("Manage Material Definitions")
            
            fixed_cats = [
                "Packaging Materials", "Maintenance Materials", "Office Materials",
                "Cleaning Materials", "Give Aways", "Clothes and Textile",
                "Food & Kitchen", "Other"
            ]

            # 1. VIEW CURRENT LIST
            with st.expander("View Full Database List"):
                current_materials = supabase.table("material_definitions").select("*").execute().data
                st.dataframe(pd.DataFrame(current_materials), use_container_width=True)
            
            st.markdown("---")
            
            # 2. ADD NEW ITEM (DETAILED)
            st.write("### ➕ Add New Item")
            with st.form("add_material_form"):
                c1, c2 = st.columns(2)
                new_cat = c1.selectbox("Category", fixed_cats)
                new_item = c2.text_input("Item Name (e.g. Cardboard Box 10kg)")
                
                st.markdown("**1. General Specs**")
                g1, g2, g3 = st.columns(3)
                use_case = g1.text_input("Use / Function")
                mat_type = g2.text_input("Material (e.g. Kraft Paper, Steel)")
                other_spec = g3.text_input("Other Specs")

                st.markdown("**2. Dimensions (cm)**")
                
                # Outer
                st.caption("Outer Dimensions")
                o1, o2, o3 = st.columns(3)
                out_l = o1.number_input("Outer L", 0.0)
                out_w = o2.number_input("Outer W", 0.0)
                out_d = o3.number_input("Outer Depth", 0.0)

                # Inner
                st.caption("Inner Dimensions")
                i1, i2, i3 = st.columns(3)
                inn_l = i1.number_input("Inner L", 0.0)
                inn_w = i2.number_input("Inner W", 0.0)
                inn_d = i3.number_input("Inner Depth", 0.0)

                if st.form_submit_button("Save New Item Definition"):
                    if new_item:
                        payload = {
                            "category": new_cat, "item_name": new_item,
                            "use_case": use_case, "mat_type": mat_type, "other_specs": other_spec,
                            "dim_outer_l": out_l, "dim_outer_w": out_w, "dim_outer_d": out_d,
                            "dim_inner_l": inn_l, "dim_inner_w": inn_w, "dim_inner_d": inn_d
                        }
                        supabase.table("material_definitions").insert(payload).execute()
                        st.success(f"Added {new_item} with full specs!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Name is required.")

            st.markdown("---")

            # 3. MODIFY ITEM
            st.write("### ✏️ Modify Item")
            
            m1, m2 = st.columns(2)
            mod_cat_filter = m1.selectbox("Filter by Category (Modify)", fixed_cats, key="mod_filter")
            
            # Fetch items
            mod_items_data = supabase.table("material_definitions").select("*").eq("category", mod_cat_filter).order('item_name').execute().data
            
            if mod_items_data:
                mod_item_names = [item['item_name'] for item in mod_items_data]
                target_item_name = m2.selectbox("Select Item to Edit", mod_item_names, key="mod_select")
                
                # Get target row
                target_row = next(item for item in mod_items_data if item["item_name"] == target_item_name)
                
                with st.form("modify_form"):
                    st.write(f"Editing: **{target_item_name}**")
                    # Use pre-filled values from DB
                    c_new_name = st.text_input("Item Name", value=target_row['item_name'])
                    c_use = st.text_input("Use / Function", value=target_row.get('use_case', ''))
                    c_mat = st.text_input("Material", value=target_row.get('mat_type', ''))
                    
                    if st.form_submit_button("Update Item"):
                        supabase.table("material_definitions").update({
                            "item_name": c_new_name,
                            "use_case": c_use,
                            "mat_type": c_mat
                        }).eq("id", target_row['id']).execute()
                        
                        st.success("Item Updated!")
                        time.sleep(1)
                        st.rerun()
            else:
                m2.warning("No items in this category.")

            st.markdown("---")

            # 4. DELETE ITEM
            st.write("### 🗑️ Delete Item")
            d1, d2, d3 = st.columns([2, 2, 1])
            
            del_cat = d1.selectbox("Filter by Category (Delete)", fixed_cats, key="del_cat")
            del_data = supabase.table("material_definitions").select("*").eq("category", del_cat).execute().data
            
            if del_data:
                del_names = [i['item_name'] for i in del_data]
                item_del = d2.selectbox("Item", del_names, key="del_item")
                if d3.button("Delete Selected"):
                    supabase.table("material_definitions").delete().eq("category", del_cat).eq("item_name", item_del).execute()
                    st.success("Deleted")
                    time.sleep(1)
                    st.rerun()
            else:
                d2.info("No items found.")
