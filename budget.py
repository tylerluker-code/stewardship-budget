import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import calendar
from datetime import datetime
import matplotlib.pyplot as plt
import glob
import random  # <--- This was the missing piece!

# --- CONFIGURATION ---
# Default path for your PC
DEFAULT_TEMPLATE_PATH = r"C:\Users\Tyler\Documents\Finances 2026\2024 budget - 12.csv"
DATA_FOLDER = "MyBudget_Data"
RULES_FILE = os.path.join(DATA_FOLDER, "category_rules.json")
INCOME_FILE = os.path.join(DATA_FOLDER, "income_sources.json")

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# --- PAGE SETUP ---
st.set_page_config(page_title="Stewardship Budget", page_icon="🌸", layout="wide")

# --- CUSTOM CSS (The "Floral" Theme) ---
st.markdown("""
    <style>
    .stApp {
        background-color: #FFF0F5;
    }
    .stButton>button {
        background-color: #D8BFD8;
        color: black;
        border-radius: 10px;
        border: 1px solid #DB7093;
    }
    h1, h2, h3 {
        color: #8B008B;
        font-family: 'Verdana';
    }
    .metric-card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #DB7093;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIC CLASSES ---

class BudgetManager:
    def __init__(self):
        self.categories = {}
        self.budget_targets = {}
        self.income_sources = self.load_income()
        self.rules = self.load_rules()
        self.default_keywords = {
            'donut': 'Eating Out', 'coffee': 'Eating Out', 'burger': 'Eating Out',
            'taco': 'Eating Out', 'pizza': 'Eating Out', 'starbucks': 'Eating Out',
            'mcdonald': 'Eating Out', 'shell': 'Gas', 'exxon': 'Gas', 'qt ': 'Gas',
            'netflix': 'Entertainment', 'spotify': 'Entertainment',
            'heb': 'Groceries', 'walmart': 'Groceries', 'kroger': 'Groceries',
            'tithe': 'Tithes', 'church': 'Tithes'
        }

    def load_rules(self):
        try:
            with open(RULES_FILE, 'r') as f: return json.load(f)
        except: return {}

    def load_income(self):
        try:
            with open(INCOME_FILE, 'r') as f: return json.load(f)
        except: return {}

    def save_rules(self):
        with open(RULES_FILE, 'w') as f: json.dump(self.rules, f)

    def save_income(self):
        with open(INCOME_FILE, 'w') as f: json.dump(self.income_sources, f)

    def load_budget_file(self, uploaded_file):
        try:
            # Determine if it's a path string or a Streamlit UploadedFile object
            if isinstance(uploaded_file, str):
                if not os.path.exists(uploaded_file): return False
                with open(uploaded_file, 'r', errors='replace') as f:
                    lines = f.readlines()
            else:
                # Streamlit file object
                stringio = uploaded_file.getvalue().decode("utf-8", errors='replace')
                lines = stringio.splitlines()

            self.categories = {}
            self.budget_targets = {}
            current_group = "Uncategorized"

            for line in lines:
                parts = line.strip().split(',')
                if not parts: continue
                first_cell = parts[0].strip().replace("- ", "").replace("* ", "")
                if "Budgeted" in line or "MONTH NUMBER" in line or not first_cell: continue

                if first_cell.isupper() and (len(parts) < 2 or parts[1] in ['', '0']):
                    current_group = first_cell
                elif current_group and first_cell and "TOTAL" not in first_cell.upper():
                    if "INCOME" in current_group.upper():
                        try: val = float(parts[1])
                        except: val = 0.0
                        self.income_sources[first_cell] = val
                    else:
                        self.categories[first_cell] = current_group
                        try: self.budget_targets[first_cell] = float(parts[1])
                        except: self.budget_targets[first_cell] = 0.0
            self.save_income()
            return True
        except Exception as e:
            st.error(f"Error reading budget file: {str(e)}")
            return False

    def parse_bank_statement(self, uploaded_file):
        try:
            df = pd.read_csv(uploaded_file, header=None)
            # Try to find header row if 0 isn't it
            if len(df.columns) < 5:
                df = pd.read_csv(uploaded_file) # Try default header
            
            # Simple Rename logic based on column position or name
            # Adapting to your previous logic
            if len(df.columns) >= 5 and 'Description' not in df.columns:
                 df = df.rename(columns={0: 'Date', 1: 'Amount', 4: 'Description'})
            
            # Ensure columns exist
            req_cols = ['Date', 'Amount', 'Description']
            if not all(col in df.columns for col in req_cols):
                st.error("CSV format not recognized. Ensure columns Date, Amount, Description exist.")
                return pd.DataFrame()

            # Clean Amount
            df['Amount'] = df['Amount'].astype(str).str.replace(r'[$,]', '', regex=True)
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
            df = df.dropna(subset=['Amount'])
            
            # Filter Spending (Negative -> Positive)
            df = df[df['Amount'] < 0].copy()
            df['Amount'] = df['Amount'].abs()
            
            df['Description'] = df['Description'].astype(str).str.strip()
            df['Category'] = None
            df['Nuance_Check'] = False
            df['Is_Cru'] = False
            return df
        except Exception as e:
            st.error(f"Could not parse file: {e}")
            return pd.DataFrame()

    def auto_categorize(self, df):
        for index, row in df.iterrows():
            if pd.notna(row['Category']): continue
            desc = str(row['Description']).lower()
            
            matched = False
            for keyword, category in self.rules.items():
                if keyword in desc:
                    df.at[index, 'Category'] = category
                    matched = True
                    break
            
            if not matched:
                for keyword, category in self.default_keywords.items():
                    if keyword in desc:
                        df.at[index, 'Category'] = category
                        matched = True; break
            
            if "amazon" in desc or "amzn" in desc or "target" in desc:
                df.at[index, 'Nuance_Check'] = True
        return df

# --- INITIALIZE SESSION STATE ---
if 'manager' not in st.session_state:
    st.session_state.manager = BudgetManager()
    # Try load default template on start
    st.session_state.manager.load_budget_file(DEFAULT_TEMPLATE_PATH)

if 'current_data' not in st.session_state:
    st.session_state.current_data = None

if 'master_filename' not in st.session_state:
    st.session_state.master_filename = None

# --- SIDEBAR ---
st.sidebar.title("🌸 Menu")
page = st.sidebar.radio("Go to:", [
    "🏠 Dashboard", 
    "🌱 Start New Month", 
    "🔄 Continue Month", 
    "💰 Manage Income", 
    "🌷 Edit Budget Categories",
    "📈 History"
])

# --- DASHBOARD PAGE ---
if page == "🏠 Dashboard":
    st.title("🌸 Stewardship Budget")
    
    # Verse
    verses = [
        "For where your treasure is, there your heart will be also. - Matthew 6:21",
        "The plans of the diligent lead surely to abundance. - Proverbs 21:5",
        "Moreover, it is required of stewards that they be found faithful. - 1 Cor 4:2"
    ]
    st.info(f"📖 {random.choice(verses)}")

    st.markdown("### Welcome Back!")
    st.write("Use the menu on the left to manage your budget. This tool works on your phone if you are connected to the same Wi-Fi!")
    
    if st.session_state.master_filename:
        st.success(f"📂 Currently working on: **{os.path.basename(st.session_state.master_filename)}**")
        if st.button("View Current Report"):
            # Load the current master file into session to view
            try:
                st.session_state.current_data = pd.read_csv(st.session_state.master_filename)
                st.write("Data Loaded. Go to 'Continue Month' to edit or view details.")
            except:
                st.error("Could not load file.")

# --- START NEW MONTH ---
elif page == "🌱 Start New Month":
    st.header("🌱 Start A New Month")
    
    col1, col2 = st.columns(2)
    with col1:
        sel_month = st.selectbox("Month", list(calendar.month_name)[1:], index=datetime.now().month-1)
    with col2:
        sel_year = st.selectbox("Year", [2024, 2025, 2026, 2027], index=2)
        
    uploaded_files = st.file_uploader("Upload Week 1 Bank CSVs (Credit/Debit)", accept_multiple_files=True, type=['csv'])
    
    if st.button("Start Budgeting"):
        if uploaded_files:
            fname = f"Master_{sel_month}_{sel_year}.csv"
            master_path = os.path.join(DATA_FOLDER, fname)
            
            dfs = []
            for up_file in uploaded_files:
                df = st.session_state.manager.parse_bank_statement(up_file)
                df = st.session_state.manager.auto_categorize(df)
                dfs.append(df)
            
            if dfs:
                combined = pd.concat(dfs, ignore_index=True)
                st.session_state.current_data = combined
                st.session_state.master_filename = master_path
                # Save immediately
                combined.to_csv(master_path, index=False)
                st.success(f"Created {fname}! Go to 'Continue Month' to categorize transactions.")
            else:
                st.error("Could not parse files.")
        else:
            st.warning("Please upload at least one file.")

# --- CONTINUE MONTH (The Core Work) ---
elif page == "🔄 Continue Month":
    st.header("🔄 Manage Transactions")
    
    # 1. Select Master File
    masters = glob.glob(os.path.join(DATA_FOLDER, "Master_*.csv"))
    masters_base = [os.path.basename(m) for m in masters]
    
    if not masters:
        st.warning("No budget files found. Please start a new month first.")
    else:
        selected_master = st.selectbox("Select Budget Month:", masters_base)
        master_path = os.path.join(DATA_FOLDER, selected_master)
        
        # Load button
        if st.button("Load Month"):
            st.session_state.current_data = pd.read_csv(master_path)
            st.session_state.master_filename = master_path
            st.success("Loaded!")

        # 2. Add New Data?
        with st.expander("📥 Upload New Transactions (Weekly Check-in)"):
            new_files = st.file_uploader("Upload New Week's CSVs", accept_multiple_files=True, type=['csv'])
            if st.button("Merge New Data"):
                if st.session_state.current_data is not None and new_files:
                    dfs = [st.session_state.current_data]
                    for nf in new_files:
                        df = st.session_state.manager.parse_bank_statement(nf)
                        df = st.session_state.manager.auto_categorize(df)
                        dfs.append(df)
                    
                    merged = pd.concat(dfs, ignore_index=True)
                    st.session_state.current_data = merged
                    merged.to_csv(master_path, index=False)
                    st.success("Merged new transactions!")
                    st.rerun()

        # 3. The Review Interface
        if st.session_state.current_data is not None:
            df = st.session_state.current_data
            
            # TABS
            tab_review, tab_report = st.tabs(["📝 Review Transactions", "📊 Monthly Report"])
            
            with tab_review:
                st.info("💡 Tip: You can edit categories directly in the table below. Changes save automatically when you click 'Save Progress'.")
                
                edit_df = df.copy()
                all_cats = sorted(st.session_state.manager.categories.keys())
                all_cats.insert(0, "Business/Cru") 
                
                edited_df = st.data_editor(
                    edit_df,
                    column_config={
                        "Category": st.column_config.SelectboxColumn(
                            "Category",
                            help="Select the budget category",
                            options=all_cats,
                            required=False
                        ),
                        "Is_Cru": st.column_config.CheckboxColumn(
                            "Cru Expense?",
                            help="Check if this is reimbursable",
                            default=False,
                        ),
                        "Nuance_Check": st.column_config.CheckboxColumn("Review Flag"),
                        "Amount": st.column_config.NumberColumn(format="$%.2f")
                    },
                    hide_index=True,
                    num_rows="dynamic"
                )
                
                if st.button("💾 Save Progress"):
                    st.session_state.current_data = edited_df
                    st.session_state.current_data.to_csv(st.session_state.master_filename, index=False)
                    st.toast("Saved successfully!", icon="✅")

            with tab_report:
                st.subheader("🌸 Monthly Summary")
                personal_df = df[df['Is_Cru'] == False]
                cru_df = df[df['Is_Cru'] == True]
                total_income = sum(st.session_state.manager.income_sources.values())
                actuals = personal_df.groupby('Category')['Amount'].sum()
                all_active_cats = set(st.session_state.manager.budget_targets.keys()) | set(actuals.index)
                
                col1, col2, col3 = st.columns(3)
                total_budget = sum(st.session_state.manager.budget_targets.values())
                total_spent = actuals.sum()
                
                col1.metric("Total Income", f"${total_income:,.2f}")
                col2.metric("Total Budget", f"${total_budget:,.2f}")
                col3.metric("Total Spent", f"${total_spent:,.2f}", delta=f"${total_budget-total_spent:,.2f}")
                
                if total_income > 0:
                    savings = total_income - total_spent
                    rate = (savings / total_income) * 100
                    st.progress(max(0, min(100, int(rate))), text=f"Savings Rate: {rate:.1f}%")

                st.divider()
                groups = {}
                for cat in all_active_cats:
                    grp = st.session_state.manager.categories.get(cat, "Uncategorized")
                    if grp not in groups: groups[grp] = []
                    groups[grp].append(cat)
                
                for group in sorted(groups.keys()):
                    st.markdown(f"#### 🌿 {group}")
                    grp_data = []
                    for cat in sorted(groups[group]):
                        b = st.session_state.manager.budget_targets.get(cat, 0.0)
                        s = actuals.get(cat, 0.0)
                        r = b - s
                        status = "✅" if r >= 0 else "⚠️"
                        grp_data.append({
                            "Category": cat,
                            "Budget": f"${b:,.2f}",
                            "Spent": f"${s:,.2f}",
                            "Remaining": f"${r:,.2f}",
                            "Status": status
                        })
                    st.dataframe(pd.DataFrame(grp_data), hide_index=True, use_container_width=True)

                if not cru_df.empty:
                    st.divider()
                    st.markdown("### 📎 Cru Reimbursements")
                    st.dataframe(cru_df[['Date', 'Description', 'Amount']], hide_index=True)
                    st.metric("Total to Submit", f"${cru_df['Amount'].sum():,.2f}")

# --- INCOME MANAGER ---
elif page == "💰 Manage Income":
    st.header("💰 Manage Income Sources")
    income_data = [{"Source": k, "Amount": v} for k, v in st.session_state.manager.income_sources.items()]
    income_df = pd.DataFrame(income_data)
    edited_income = st.data_editor(income_df, num_rows="dynamic", use_container_width=True)
    if st.button("Save Income"):
        new_income = {}
        for index, row in edited_income.iterrows():
            if row["Source"]:
                new_income[row["Source"]] = float(row["Amount"])
        st.session_state.manager.income_sources = new_income
        st.session_state.manager.save_income()
        st.success("Income updated!")

# --- CATEGORY EDITOR ---
elif page == "🌷 Edit Budget Categories":
    st.header("🌷 Edit Budget Categories")
    cat_data = []
    for cat, grp in st.session_state.manager.categories.items():
        amt = st.session_state.manager.budget_targets.get(cat, 0.0)
        cat_data.append({"Group": grp, "Category": cat, "Budget Amount": amt})
        
    cat_df = pd.DataFrame(cat_data)
    edited_cats = st.data_editor(cat_df, num_rows="dynamic", use_container_width=True)
    
    if st.button("Save Budget Settings"):
        new_cats = {}
        new_targets = {}
        for index, row in edited_cats.iterrows():
            if row["Category"]:
                new_cats[row["Category"]] = row["Group"]
                new_targets[row["Category"]] = float(row["Budget Amount"])
        st.session_state.manager.categories = new_cats
        st.session_state.manager.budget_targets = new_targets
        
        with open(os.path.join(DATA_FOLDER, "budget_targets.json"), 'w') as f:
            json.dump(new_targets, f)
        with open(os.path.join(DATA_FOLDER, "categories_map.json"), 'w') as f:
            json.dump(new_cats, f)
        st.success("Categories updated!")

# --- HISTORY ---
elif page == "📈 History":
    st.header("📈 Spending Trends")
    masters = glob.glob(os.path.join(DATA_FOLDER, "Master_*.csv"))
    data_points = []
    for m in masters:
        try:
            name = os.path.basename(m).replace("Master_", "").replace(".csv", "")
            df = pd.read_csv(m)
            if 'Is_Cru' in df.columns: df = df[df['Is_Cru'] == False]
            total = df['Amount'].sum()
            data_points.append({"Month": name, "Spent": total})
        except: pass
        
    if data_points:
        chart_df = pd.DataFrame(data_points)
        st.line_chart(chart_df.set_index("Month"))
        st.dataframe(chart_df)
    else:
        st.info("No history yet.")