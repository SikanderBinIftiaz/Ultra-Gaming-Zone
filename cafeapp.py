import streamlit as st
import pickle
import os
from datetime import datetime
import pandas as pd

# Define data storage file
PKL_FILE = "ultra_cafe_data.pkl"

# ==========================================
# 1. DATABASE / PICKLE FUNCTIONS
# ==========================================
def load_database():
    """Loads database from pickle or creates a fresh template."""
    if os.path.exists(PKL_FILE):
        try:
            with open(PKL_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return init_new_db()
    else:
        return init_new_db()

def init_new_db():
    return {
        "active_cabins": {},   # Currently running sessions
        "pc_history": [],      # Completed PC logs
        "other_sales": []      # Snack/Misc sale logs
    }

def save_database(data):
    """Saves the current state back to the pickle file."""
    with open(PKL_FILE, 'wb') as f:
        pickle.dump(data, f)

def calculate_rate(start_str, end_str):
    """Business Logic: 40 Rs for <= 30 mins, 70 Rs/hr for > 30 mins."""
    fmt = "%Y-%m-%d %H:%M:%S"
    t1 = datetime.strptime(start_str, fmt)
    t2 = datetime.strptime(end_str, fmt)
    
    diff_mins = int((t2 - t1).total_seconds() / 60)
    if diff_mins <= 0:
        return 0, 0
    
    if diff_mins <= 30:
        charge = 40.0
    else:
        charge = round((diff_mins / 60.0) * 70.0, 2)
        
    return diff_mins, charge

# Initialize app state data
if "db" not in st.session_state:
    st.session_state.db = load_database()

db = st.session_state.db

# ==========================================
# 2. STREAMLIT APP FRONTEND LAYOUT
# ==========================================
st.set_page_config(page_title="Ultra Gaming Zone Dashboard", layout="wide")

# Main Branding Header
st.markdown("<h1 style='text-align: center; color: #00ffcc;'>🎮 ULTRA GAMING ZONE 🎮</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center; color: gray;'>Internet Cafe & Gaming Center Management System</h4>", unsafe_allow_html=True)
st.write("---")

# ----------------- SIDEBAR PANEL -----------------
st.sidebar.header("🕹️ Counter Controls")

# Form 1: Start Session
with st.sidebar.form("start_session_form", clear_on_submit=True):
    st.subheader("▶️ Start Timing")
    cabin_input = st.text_input("Cabin / PC Number:").strip()
    
    # Sub-option to override time or use current system time
    use_custom_start = st.checkbox("Manual Time Entry?")
    custom_start_time = st.text_input("Custom Time (YYYY-MM-DD HH:MM:SS)", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    submit_start = st.form_submit_button("Start Session")
    
    if submit_start:
        if not cabin_input:
            st.error("Please enter a Cabin ID!")
        elif cabin_input in db["active_cabins"]:
            st.warning(f"Cabin {cabin_input} is already occupied!")
        else:
            start_time = custom_start_time if use_custom_start else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db["active_cabins"][cabin_input] = start_time
            save_database(db)
            st.success(f"Successfully started timing for {cabin_input}")
            st.rerun()

# Form 2: Other Sales
with st.sidebar.form("other_sales_form", clear_on_submit=True):
    st.subheader("🍿 Other Sales Tracker")
    item_name = st.text_input("Item / Product Name:").strip()
    item_cost = st.number_input("Price Collected (Rs):", min_value=0.0, step=5.0)
    submit_sale = st.form_submit_button("Add Misc Sale")
    
    if submit_sale:
        if not item_name or item_cost <= 0:
            st.error("Enter a valid Item Name and Price!")
        else:
            sale_record = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "item": item_name,
                "price": item_cost
            }
            db["other_sales"].append(sale_record)
            save_database(db)
            st.success(f"Logged sale: {item_name} (Rs {item_cost})")
            st.rerun()


# ----------------- MAIN MAIN METRICS ROW -----------------
today = datetime.now().strftime("%Y-%m-%d")
this_month = datetime.now().strftime("%Y-%m")

day_pc = sum(x['charge'] for x in db['pc_history'] if x['date'] == today)
day_sales = sum(y['price'] for y in db['other_sales'] if y['date'] == today)

month_pc = sum(x['charge'] for x in db['pc_history'] if x['date'].startswith(this_month))
month_sales = sum(y['price'] for y in db['other_sales'] if y['date'].startswith(this_month))

col_m1, col_m2 = st.columns(2)
col_m1.metric(label="💰 TODAY'S TOTAL EARNINGS", value=f"Rs {day_pc + day_sales:.2f}")
col_m2.metric(label="📈 MONTHLY TOTAL REVENUE", value=f"Rs {month_pc + month_sales:.2f}")

st.write("---")

# ----------------- TABS SYSTEM FOR DATA VIEW -----------------
tab_live, tab_history = st.tabs(["🖥️ Live Counter Dashboard", "📖 Past Transaction Ledger"])

# TAB 1: LIVE COUNTER
with tab_live:
    st.subheader("Occupied PCs / Running Cabins")
    
    if not db["active_cabins"]:
        st.info("No active sessions right now. All cabins are free!")
    else:
        # Construct dynamic layout table for live actions
        live_data = []
        for cabin, t_start in db["active_cabins"].items():
            live_data.append({"Cabin ID": cabin, "Time In (Login Time)": t_start})
            
        df_live = pd.DataFrame(live_data)
        st.dataframe(df_live, use_container_width=True)
        
        # Action Element to end session
        st.subheader("⏹️ End Session & Calculate Bill")
        cabin_to_end = st.selectbox("Select Cabin leaving right now:", list(db["active_cabins"].keys()))
        
        use_custom_end = st.checkbox("Manual End Time Override?")
        custom_end_time = st.text_input("Custom End Time (YYYY-MM-DD HH:MM:SS)", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        if st.button("Stop Timer & Generate Invoice", type="primary"):
            start_time_str = db["active_cabins"].pop(cabin_to_end)
            end_time_str = custom_end_time if use_custom_end else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            minutes, final_cost = calculate_rate(start_time_str, end_time_str)
            
            log_record = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "cabin": cabin_to_end,
                "start": start_time_str,
                "end": end_time_str,
                "duration": minutes,
                "charge": final_cost
            }
            db["pc_history"].append(log_record)
            save_database(db)
            
            # Print Alert Receipt Invoice directly onto the web interface
            st.balloons()
            st.success(f"### 🧾 INVOICE GENERATED FOR {cabin_to_end}")
            st.info(f"**Total Use duration:** {minutes} Minutes | **Grand Bill Due:** Rs {final_cost}")
            st.session_state.ended_receipt = True
            
            # Tiny delay simulation helper to cleanly update lists
            st.button("Acknowledge & Refresh Data Tables")

# TAB 2: HISTORIC LEDGER
with tab_history:
    st.subheader("All Past Digital Ledger Entries")
    
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.markdown("#### 💻 Past PC Sessions")
        if db["pc_history"]:
            df_pc_hist = pd.DataFrame(db["pc_history"])
            # Reordering columns for presentation flow
            df_pc_hist = df_pc_hist[['date', 'cabin', 'start', 'end', 'duration', 'charge']]
            df_pc_hist.columns = ['Date', 'Cabin #', 'Time In', 'Time Out', 'Duration (Mins)', 'Bill (Rs)']
            st.dataframe(df_pc_hist.iloc[::-1], use_container_width=True) # Reverse to see latest on top
        else:
            st.caption("No historical PC sessions logged yet.")
            
    with col_t2:
        st.markdown("#### 🥤 Miscellaneous Counter Sales")
        if db["other_sales"]:
            df_sales_hist = pd.DataFrame(db["other_sales"])
            df_sales_hist.columns = ['Transaction Date', 'Product / Service Name', 'Price Earned (Rs)']
            st.dataframe(df_sales_hist.iloc[::-1], use_container_width=True)
        else:
            st.caption("No product accessory sales saved yet.")