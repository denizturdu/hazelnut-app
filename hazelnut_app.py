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

# --- LOGIN ---
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
        
    module = st.sidebar.radio("Navigate", ["1. Purchase (Satın Alma)", "2. Intake (Mal Kabul)"])

# ==========================
    # MODULE 1: PURCHASE
    # ==========================
    if module == "1. Purchase (Satın Alma)":
        st.title("Module 1: Purchasing Hub")
        
        # 1. DEFINE THE NEW CATEGORIES
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
        
        # Combine them for the dropdown
        all_options = hazelnut_group + general_group
        
        type_selector = st.selectbox("Purchase Category", all_options)
        
        # --- LOGIC FOR HAZELNUT GROUP (Detailed Form) ---
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
                
                # UPDATED HAZELNUT TYPES LIST
                hazelnut_type = c9.selectbox("Hazelnut Variety", [
                    "Karışık", "Giresun Tombul", "Çakıldak", "Kara", 
                    "Sivri", "Palaz", "Badem", "Foşa", "Yomra"
                ])
                
                st.markdown("---")
                st.subheader("2. Quality & Randıman (Eksper)")
                
                # ROW 1: RANDIMAN
                q1, q2, q3 = st.columns(3)
                sample_w = q1.number_input("Sample Inshell Size (g)", value=250.0)
                good_k = q2.number_input("Good Kernel (g)", value=0.0)
                shriv_k = q3.number_input("Shrivelled Kernel (g)", value=0.0)
                
                # ROW 2: DEFECTS
                d1, d2, d3 = st.columns(3)
                vis_rot = d1.number_input("Visible Rotten (g)", value=0.0)
                hid_rot = d2.number_input("Hidden Rotten (g)", value=0.0)
                tumor = d3.number_input("Tumorous (g)", value=0.0)

                # ROW 3: SIZING
                s1, s2, s3 = st.columns(3)
                size_1 = s1.number_input("Size 1 %>13mm (%)", value=0.0)
                under_size = s2.number_input("Undersize %<9mm (%)", value=0.0)
                moisture = s3.number_input("Moisture (%)", 0.0, 20.0, 5.0)
                
                # CALCULATE BUTTON
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
                else:
                    gross_price = st.number_input("Gross Price (50 Rand)", value=120.0)
                    
                    # Formulas
                    net_price_50 = gross_price / 1.0245
                    unit_price = net_price_50 * (randiman / 50.0)
                    total_val = unit_price * net_weight
                    
                    st.write(f"**Net Price (50 Rand):** {net_price_50:.2f} TL")
                    st.write(f"**Actual Price (per kg):** {unit_price:.2f} TL")
                    st.info(f"**TOTAL VALUE:** {total_val:,.2f} TL")

                    # Payment
                    pay_col1, pay_col2 = st.columns(2)
                    pay_amount = pay_col1.number_input("Payment Amount (TL)", value=0.0)
                    pay_method = pay_col2.selectbox("Way of Payment", ["Cash", "Bank Transfer", "Check"])
                    
                    remaining = total_val - pay_amount
                    st.metric("Remaining Balance", f"{remaining:,.2f} TL")

                # SAVE BUTTON
                submit_save = st.form_submit_button("✅ Create Contract & Save")
                
                if submit_save:
                    payload = {
                        "created_by": st.session_state.user.email,
                        "status": "Pending Arrival",
                        # We use the selector value (e.g. "Hazelnut Kernels") as the Category
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

        # --- LOGIC FOR GENERAL GROUP (Materials, Machines, Services) ---
        else:
            st.subheader(f"Purchase Order: {type_selector}")
            with st.form("general_form"):
                c1, c2 = st.columns(2)
                supplier = c1.text_input("Supplier / Provider")
                item_desc = c2.text_input("Description / Item Name")
                
                c3, c4 = st.columns(2)
                qty = c3.number_input("Quantity", min_value=1.0, value=1.0)
                price = c4.number_input("Total Estimated Cost (TL)", min_value=0.0)
                
                submit_general = st.form_submit_button(f"✅ Create {type_selector} Order")
                
                if submit_general:
                    payload = {
                        "category": type_selector, # Will be 'Materials', 'Machines', or 'Services'
                        "supplier": supplier,
                        "item_type": item_desc,
                        "qty_ordered": qty,
                        "total_value": price,
                        "status": "Pending Arrival",
                        "created_by": st.session_state.user.email
                    }
                    try:
                        insert_record("purchases", payload)
                        st.success(f"{type_selector} Order Saved!")
                    except Exception as e:
                        st.error(f"Error saving: {e}")
    # ==========================
    # MODULE 2: INTAKE
    # ==========================
    elif module == "2. Intake (Mal Kabul)":
        st.title("Module 2: Factory Gate Intake")
        
        # Fetch Pending Items
        try:
            response = supabase.table("purchases").select("*").eq("status", "Pending Arrival").execute()
            pending_df = pd.DataFrame(response.data)
            
            if not pending_df.empty:
                st.subheader("Expected Arrivals")
                # Show key columns
                st.dataframe(pending_df[["id", "supplier", "item_type", "qty_ordered", "location"]])
                
                st.markdown("---")
                st.subheader("Process Arrival")
                
                po_ids = pending_df['id'].tolist()
                selected_id = st.selectbox("Select Purchase ID", po_ids)
                
                # Get the selected row data
                selected_row = pending_df[pending_df['id'] == selected_id].iloc[0]
                
                st.info(f"Receiving: {selected_row['item_type']} from {selected_row['supplier']}")
                
                with st.form("intake_confirm"):
                    c1, c2 = st.columns(2)
                    plate = c1.text_input("Plate Number")
                    waybill = c2.text_input("Waybill No")
                    
                    received_qty = st.number_input("Actual Received Quantity (kg/count)", value=float(selected_row['qty_ordered']))
                    loc_warehouse = st.text_input("Warehouse Location (e.g. Silo 1)")
                    
                    if st.form_submit_button("Confirm Arrival"):
                        # 1. Update Purchase Status
                        supabase.table("purchases").update({"status": "Received"}).eq("id", selected_id).execute()
                        
                        # 2. Insert into Intake Log
                        intake_payload = {
                            "po_id": int(selected_id),
                            "plate_number": plate,
                            "waybill_no": waybill,
                            "received_qty": received_qty,
                            "variance": received_qty - float(selected_row['qty_ordered']),
                            "location_in_warehouse": loc_warehouse,
                            "created_by": st.session_state.user.email
                        }
                        insert_record("intake_log", intake_payload)
                        st.success("Arrival Confirmed! Inventory Updated.")
                        time.sleep(1)
                        st.rerun()
            else:
                st.info("No pending shipments found.")
                
        except Exception as e:
            st.error(f"Error loading data: {e}")


# --- LOGIC FOR GENERAL GROUP (Materials, Machines, Services) ---
        else:
            st.subheader(f"Purchase Order: {type_selector}")
            
            # SPECIAL LOGIC FOR MATERIALS: Fetch from DB
            if type_selector == "Materials":
                # 1. Define the 8 Main Categories
                material_cats = [
                    "Packaging Materials", "Maintenance Materials", "Office Materials",
                    "Cleaning Materials", "Give Aways", "Clothes and Textile",
                    "Food & Kitchen", "Other"
                ]
                
                with st.form("material_form"):
                    c1, c2 = st.columns(2)
                    supplier = c1.text_input("Supplier")
                    
                    # Category Selector
                    selected_mat_cat = c2.selectbox("Material Category", material_cats)
                    
                    # Item Selector (Dynamic)
                    # We fetch items from DB that match the selected category
                    # Note: In a real app, we might cache this to avoid slow loading, 
                    # but for now we query directly.
                    try:
                        response = supabase.table("material_definitions").select("item_name").eq("category", selected_mat_cat).execute()
                        # Convert list of dicts [{'item_name': 'X'}, {'item_name': 'Y'}] to list ['X', 'Y']
                        item_list = [row['item_name'] for row in response.data]
                        
                        # If list is empty, show a text box so they aren't stuck
                        if item_list:
                            item_name = st.selectbox("Select Item", item_list)
                        else:
                            st.warning(f"No items found in DB for {selected_mat_cat}. Please ask Admin to add them.")
                            item_name = st.text_input("Type Item Name manually")
                            
                    except:
                        item_name = st.text_input("Item Name")

                    c3, c4 = st.columns(2)
                    qty = c3.number_input("Quantity", min_value=1.0, value=1.0)
                    price = c4.number_input("Total Estimated Cost (TL)", min_value=0.0)
                    
                    submit_mat = st.form_submit_button("✅ Create Material Order")
                    
                    if submit_mat:
                        payload = {
                            "category": "Materials",
                            "item_sub_type": selected_mat_cat, # We save the category here
                            "supplier": supplier,
                            "item_type": item_name,
                            "qty_ordered": qty,
                            "total_value": price,
                            "status": "Pending Arrival",
                            "created_by": st.session_state.user.email
                        }
                        insert_record("purchases", payload)
                        st.success("Material Order Saved!")

            # LOGIC FOR MACHINES & SERVICES (Keep simple for now)
            else:
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
