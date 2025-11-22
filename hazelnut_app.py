import streamlit as st
import pandas as pd
from db_utils import supabase, login_user, insert_record
import time

st.set_page_config(page_title="Hazelnut Factory Manager", layout="wide")

# --- HELPER: RANDIMAN CALCULATOR ---
def calculate_randiman(good_kernel, shrivelled_kernel):
    # Formula: (Good Kernel + (Shrivelled / 2)) * 2
    try:
        r = (good_kernel + (shrivelled_kernel / 2)) * 2
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
        
        type_selector = st.selectbox("Purchase Category", ["Hazelnut (Fındık)", "Materials/Goods", "Services"])
        
        if type_selector == "Hazelnut (Fındık)":
            with st.form("hazelnut_form"):
                st.subheader("1. Supplier & Origin")
                c1, c2, c3 = st.columns(3)
                supplier = c1.text_input("Supplier Name")
                sup_type = c2.selectbox("Supplier Type", ["Farmer", "Merchant", "Company"])
                reg_type = c3.selectbox("Registration Type", ["Purchased", "Loaned (Emanet)"])
                
                c4, c5 = st.columns(2)
                location = c4.selectbox("Place of Registration", ["Factory", "Field", "Store"])
                hazelnut_type = c5.selectbox("Hazelnut Type", ["Levant", "Giresun", "Akçakoca"])
                
                st.markdown("---")
                st.subheader("2. Quality & Randıman")
                
                q1, q2, q3, q4 = st.columns(4)
                sample_w = q1.number_input("Sample Weight (g)", value=50.0)
                good_k = q2.number_input("Good Kernel (g)", value=0.0)
                shriv_k = q3.number_input("Shrivelled Kernel (g)", value=0.0)
                
                # Live Calc
                randiman = calculate_randiman(good_k, shriv_k)
                q4.metric("Calculated Randıman", f"{randiman:.2f}%")
                
                moisture = st.number_input("Moisture (%)", 0.0, 20.0, 5.0)

                st.markdown("---")
                st.subheader("3. Financials")
                net_weight = st.number_input("Total Net Weight (kg)", min_value=0.0)
                
                # Financial Logic
                if reg_type == "Loaned (Emanet)":
                    st.info("Transaction is Emanet. Value is 0 TL.")
                    gross_price = 0.0
                    net_price_50 = 0.0
                    unit_price = 0.0
                    total_val = 0.0
                else:
                    gross_price = st.number_input("Gross Price (50 Rand)", value=120.0)
                    
                    # Formulas
                    net_price_50 = gross_price / 1.0245
                    unit_price = net_price_50 * (randiman / 50.0)
                    total_val = unit_price * net_weight
                    
                    st.write(f"**Net Price (50 Rand):** {net_price_50:.2f} TL")
                    st.write(f"**Actual Price (per kg):** {unit_price:.2f} TL")
                    st.success(f"**TOTAL VALUE:** {total_val:,.2f} TL")

                submit = st.form_submit_button("Create Contract")
                
                if submit:
                    payload = {
                        "category": "Hazelnut",
                        "supplier": supplier,
                        "supplier_type": sup_type,
                        "reg_type": reg_type,
                        "location": location,
                        "item_type": hazelnut_type,
                        "sample_weight": sample_w,
                        "good_kernel": good_k,
                        "shrivelled_kernel": shriv_k,
                        "calculated_randiman": randiman,
                        "moisture": moisture,
                        "qty_ordered": net_weight,
                        "gross_price_50": gross_price,
                        "net_price_50": net_price_50,
                        "actual_unit_price": unit_price,
                        "total_value": total_val,
                        "created_by": st.session_state.user.email,
                        "status": "Pending Arrival"
                    }
                    try:
                        insert_record("purchases", payload)
                        st.success("Contract Saved to Database!")
                    except Exception as e:
                        st.error(f"Error saving: {e}")

        elif type_selector == "Materials/Goods":
            with st.form("material_form"):
                supplier = st.text_input("Supplier")
                item_name = st.text_input("Item Name (e.g. Jute Bags)")
                qty = st.number_input("Quantity", min_value=1.0)
                if st.form_submit_button("Order Material"):
                    payload = {
                        "category": "Material",
                        "supplier": supplier,
                        "item_type": item_name,
                        "qty_ordered": qty,
                        "status": "Pending Arrival",
                        "created_by": st.session_state.user.email
                    }
                    insert_record("purchases", payload)
                    st.success("Material Order Placed!")

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
