import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np
import json
import random
import time
from datetime import datetime

# --- HARDCODED DEFAULTS ---
DEFAULT_BUDGET = [
    {"Group": "Giving", "Category": "Tithe", "BudgetAmount": 500.0},
    {"Group": "Housing", "Category": "Mortgage/Rent", "BudgetAmount": 1500.0},
    {"Group": "Food", "Category": "Groceries", "BudgetAmount": 600.0},
    {"Group": "Food", "Category": "Eating Out", "BudgetAmount": 150.0},
    {"Group": "Transportation", "Category": "Gas", "BudgetAmount": 200.0},
    {"Group": "Lifestyle", "Category": "Entertainment", "BudgetAmount": 100.0},
    {"Group": "Savings", "Category": "Emergency Fund", "BudgetAmount": 200.0},
    {"Group": "Business", "Category": "Business/Cru", "BudgetAmount": 0.0}
]

# --- PAGE SETUP ---
st.set_page_config(page_title="Stewardship App", page_icon="🌸", layout="wide")

# --- CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #FFF0F5; }
    .stButton>button { background-color: #D8BFD8; color: black; border-radius: 10px; border: 1px solid #DB7093; }
    h1, h2, h3 { color: #8B008B; font-family: 'Verdana'; }
    div[data-testid="stMetricValue"] { font-size: 24px; color: #4A4A4A; }
    </style>
    """, unsafe_allow_html=True)

# --- AUTHENTICATION ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    if st.session_state.password_correct:
        return True
    
    st.title("🔒 Login")
    pwd = st.text_input("Enter Family Password", type="password")
    
    # --- DEBUGGER (Visible only on login) ---
    with st.expander("🔧 Connection Debugger"):
        try:
            if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
                st.success("✅ Secrets File Found")
                if "service_account" in st.secrets["connections"]["gsheets"]:
                    st.success("✅ Service Account Section Found")
                else:
                    st.error("❌ Service Account Section Missing")
            else:
                st.error("❌ 'connections.gsheets' section missing in Secrets")
        except:
            st.error("❌ Could not read secrets")

    if st.button("Log In"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("Incorrect password")
    return False

# --- DATA MANAGER (FORCE AUTH) ---
class CloudBudgetManager:
    def __init__(self):
        # 1. Manually grab the service account dict from secrets
        try:
            raw_creds = st.secrets["connections"]["gsheets"]["service_account"]
            # 2. Pass it explicitly to the connection
            self.conn = st.connection(
                "gsheets", 
                type=GSheetsConnection, 
                service_account=raw_creds
            )
        except Exception as e:
            st.error(f"Secrets Error: {e}")
            self.conn = st.connection("gsheets", type=GSheetsConnection)

    def get_data(self, worksheet_name):
        try:
            return self.conn.read(worksheet=worksheet_name, ttl=0)
        except:
            return pd.DataFrame()

    def update_data(self, df, worksheet_name):
        try:
            if df.empty: return
            self.conn.update(worksheet=worksheet_name, data=df)
            st.toast(f"Saved to cloud ({worksheet_name})! ☁️", icon="✅")
        except Exception as e:
            st.error(f"Write Error on '{worksheet_name}': {str(e)}")
            st.info("Try changing your Google Sheet permissions to 'Restricted' (only shared with the bot).")

def auto_categorize(df, rules, defaults):
    if 'Category' not in df.columns: df['Category'] = None
    if 'Nuance_Check' not in df.columns: df['Nuance_Check'] = False
    for index, row in df.iterrows():
        if pd.notna(row['Category']): continue
        desc = str(row['Description']).lower()
        matched = False
        for keyword, category in rules.items():
            if keyword in desc:
                df.at[index, 'Category'] = category
                matched = True
                break
        if not matched:
            for keyword, category in defaults.items():
                if keyword in desc:
                    df.at[index, 'Category'] = category
                    break
        if "amazon" in desc or "amzn" in desc or "target" in desc:
            df.at[index, 'Nuance_Check'] = True
    return df

# --- MAIN APP ---
if check_password():
    manager = CloudBudgetManager()
    
    st.caption("🔄 Syncing with Cloud...")
    rules_df = manager.get_data("BudgetRules")
    
    if rules_df.empty:
        try:
            st.info("Initializing Default Budget Rules...")
            rules_df = pd.DataFrame(DEFAULT_BUDGET)
            rules_df["Keywords"] = ""
            manager.update_data(rules_df, "BudgetRules")
            time.sleep(2)
            st.rerun()
        except Exception as e:
            st.warning(f"Init Error: {e}")

    categories = {} 
    targets = {}    
    custom_rules = {} 
    
    if not rules_df.empty:
        for i, row in rules_df.iterrows():
            if pd.notna(row['Category']):
                categories[row['Category']] = row['Group']
                targets[row['Category']] = row['BudgetAmount']
                if 'Keywords' in row and pd.notna(row['Keywords']) and row['Keywords']:
                    try:
                        kws = json.loads(row['Keywords'])
                        for k in kws: custom_rules[k] = row['Category']
                    except: pass

    tx_df = manager.get_data("Transactions")
    if tx_df.empty: tx_df = pd.DataFrame(columns=["Date", "Description", "Amount", "Category", "Is_Cru", "Nuance_Check"])

    inc_df = manager.get_data("Income")
    if inc_df.empty: inc_df = pd.DataFrame(columns=["Source", "Amount"])

    # --- SIDEBAR ---
    st.sidebar.title("🌸 Menu")
    page = st.sidebar.radio("Go to:", ["🏠 Dashboard", "📥 Add Transactions", "🔄 Review & Edit", "💰 Income & Budget"])

    # --- DASHBOARD ---
    if page == "🏠 Dashboard":
        st.title("🌸 Stewardship Dashboard")
        
        with st.expander("📅 Filter Date Range"):
            if not tx_df.empty and 'Date' in tx_df.columns:
                tx_df['Date'] = pd.to_datetime(tx_df['Date'])
                min_date = tx_df['Date'].min().date()
                max_date = tx_df['Date'].max().date()
                d_range = st.date_input("Select Range", [min_date, max_date])
                
                if len(d_range) == 2:
                    mask = (tx_df['Date'].dt.date >= d_range[0]) & (tx_df['Date'].dt.date <= d_range[1])
                    dashboard_tx = tx_df[mask]
                else:
                    dashboard_tx = tx_df
            else:
                dashboard_tx = tx_df

        personal_tx = dashboard_tx[dashboard_tx['Is_Cru'] == False] if not dashboard_tx.empty else dashboard_tx
        total_income = inc_df['Amount'].sum() if not inc_df.empty else 0.0
        total_spent = personal_tx['Amount'].sum() if not personal_tx.empty else 0.0
        total_budget = sum(targets.values())
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Income", f"${total_income:,.2f}")
        c2.metric("Planned Budget", f"${total_budget:,.2f}")
        c3.metric("Actual Spent", f"${total_spent:,.2f}", delta=f"${total_budget-total_spent:,.2f}")
        
        if total_income > 0:
            rate = ((total_income - total_spent) / total_income) * 100
            st.progress(max(0, min(100, int(rate))), text=f"Savings Rate: {rate:.1f}%")

        st.divider()
        st.subheader("🌿 Budget Health")
        if not personal_tx.empty:
            actuals = personal_tx.groupby('Category')['Amount'].sum()
            groups = {}
            active_cats = set(targets.keys()) | set(actuals.index)
            for c in active_cats:
                g = categories.get(c, "Uncategorized")
                if g not in groups: groups[g] = []
                groups[g].append(c)
            
            for g in sorted(groups.keys()):
                st.caption(f"**{g}**")
                g_data = []
                for cat in groups[g]:
                    b = targets.get(cat, 0.0)
                    s = actuals.get(cat, 0.0)
                    rem = b - s
                    g_data.append({"Category": cat, "Budget": b, "Spent": s, "Remaining": rem})
                st.dataframe(pd.DataFrame(g_data), hide_index=True, use_container_width=True)

    # --- ADD TRANSACTIONS ---
    elif page == "📥 Add Transactions":
        st.header("📥 Add Transactions")
        tab_manual, tab_csv = st.tabs(["✍️ Manual Entry (Single)", "📂 Bulk Upload (CSV)"])
        
        with tab_manual:
            st.info("Use this when you are at the store to check budget and add expense.")
            all_cats = sorted(list(categories.keys()))
            if not all_cats:
                st.warning("No categories found! Waiting for sync...")
                sel_cat = None
            else:
                sel_cat = st.selectbox("Category", all_cats, index=0)
            
            if sel_cat:
                b_val = targets.get(sel_cat, 0.0)
                if not tx_df.empty:
                    tx_df['Is_Cru'] = tx_df['Is_Cru'].astype(bool)
                    curr_s = tx_df[(tx_df['Category'] == sel_cat) & (tx_df['Is_Cru'] == False)]['Amount'].sum()
                else:
                    curr_s = 0.0
                rem_val = b_val - curr_s
                
                col_m1, col_m2 = st.columns(2)
                col_m1.metric(f"Budget for {sel_cat}", f"${b_val:,.0f}")
                col_m2.metric(f"⚠️ Remaining Available", f"${rem_val:,.2f}", delta_color="normal" if rem_val > 0 else "inverse")
                st.divider()

            c1, c2 = st.columns(2)
            d_date = c1.date_input("Date", datetime.now())
            d_amt = c2.number_input("Amount ($)", min_value=0.0, step=0.01)
            d_desc = st.text_input("Description (Vendor)", placeholder="e.g. HEB, Shell")
            is_cru = st.checkbox("Is this a Cru Expense? (Reimbursable)")
            
            if st.button("Add Transaction", type="primary"):
                if d_amt > 0:
                    new_row = pd.DataFrame([{
                        "Date": d_date.strftime("%Y-%m-%d"),
                        "Description": d_desc,
                        "Amount": d_amt,
                        "Category": sel_cat,
                        "Is_Cru": is_cru,
                        "Nuance_Check": False
                    }])
                    updated_df = pd.concat([tx_df, new_row], ignore_index=True)
                    manager.update_data(updated_df, "Transactions")
                    st.success("Transaction Added!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Please enter an amount.")

        with tab_csv:
            st.info("Upload your weekly bank export here.")
            uploaded_files = st.file_uploader("Choose CSV files", accept_multiple_files=True, type='csv')
            if st.button("Process & Merge CSVs"):
                if uploaded_files:
                    new_dfs = []
                    for f in uploaded_files:
                        try:
                            temp = pd.read_csv(f, header=None)
                            if len(temp.columns) < 5: temp = pd.read_csv(f)
                            if 'Description' not in temp.columns:
                                temp = temp.rename(columns={0: 'Date', 1: 'Amount', 4: 'Description'})
                            
                            temp['Amount'] = temp['Amount'].astype(str).str.replace(r'[$,]', '', regex=True)
                            temp['Amount'] = pd.to_numeric(temp['Amount'], errors='coerce')
                            temp = temp.dropna(subset=['Amount'])
                            temp = temp[temp['Amount'] < 0].copy()
                            temp['Amount'] = temp['Amount'].abs()
                            temp['Category'] = None
                            temp['Is_Cru'] = False
                            temp['Nuance_Check'] = False
                            
                            defaults = {
                                'donut': 'Eating Out', 'shell': 'Gas', 'heb': 'Groceries', 
                                'walmart': 'Groceries', 'netflix': 'Entertainment'
                            }
                            temp = auto_categorize(temp, custom_rules, defaults)
                            new_dfs.append(temp)
                        except Exception as e:
                            st.error(f"Error parsing {f.name}: {e}")
                    
                    if new_dfs:
                        new_data = pd.concat(new_dfs)
                        combined = pd.concat([tx_df, new_data], ignore_index=True)
                        combined = combined.drop_duplicates(subset=['Date', 'Description', 'Amount'])
                        manager.update_data(combined, "Transactions")
                        st.success(f"Added {len(new_data)} transactions! Go to 'Review' tab.")

    # --- REVIEW ---
    elif page == "🔄 Review & Edit":
        st.header("📝 Review Transactions")
        view_mode = st.radio("Show:", ["Needs Review (Ambiguous)", "All Transactions"])
        
        if view_mode == "Needs Review (Ambiguous)":
            mask = (tx_df['Category'].isnull()) | (tx_df['Nuance_Check'] == True)
            edit_view = tx_df[mask].copy()
        else:
            edit_view = tx_df.copy()
            
        if edit_view.empty:
            st.success("Nothing to review! Great job.")
        else:
            cat_options = sorted(list(categories.keys()))
            cat_options.insert(0, "Business/Cru")
            
            edited_view = st.data_editor(
                edit_view,
                column_config={
                    "Category": st.column_config.SelectboxColumn("Category", options=cat_options),
                    "Is_Cru": st.column_config.CheckboxColumn("Cru Expense"),
                    "Nuance_Check": st.column_config.CheckboxColumn("Review Needed")
                },
                use_container_width=True,
                num_rows="dynamic"
            )
            
            if st.button("Save Changes"):
                tx_df.update(edited_view)
                manager.update_data(tx_df, "Transactions")

    # --- SETTINGS ---
    elif page == "💰 Income & Budget":
        st.header("Settings")
        t1, t2 = st.tabs(["Income", "Budget Categories"])
        
        with t1:
            edited_inc = st.data_editor(inc_df, num_rows="dynamic", use_container_width=True)
            if st.button("Save Income"): manager.update_data(edited_inc, "Income")
        
        with t2:
            st.info("Edit your budget targets here. Changes save to the cloud.")
            edited_rules = st.data_editor(rules_df[['Category', 'Group', 'BudgetAmount']], num_rows="dynamic", use_container_width=True)
            if st.button("Save Categories"):
                manager.update_data(edited_rules, "BudgetRules")
