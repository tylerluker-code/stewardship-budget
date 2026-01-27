import streamlit as st
import pandas as pd
import numpy as np
import json
import time
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from github import Github
from io import StringIO

# --- CONFIGURATION ---
BRANCH = "main"
FILE_PATHS = {
    "transactions": "data/transactions.csv",
    "budget_rules": "data/budget_rules.csv",
    "income": "data/income.csv"
}

RECIPIENTS = ["tyler.luker@cru.org", "marianna.luker@cru.org"]

# --- STEWARDSHIP VERSES ---
STEWARDSHIP_VERSES = [
    "“Honor the Lord with your wealth, with the firstfruits of all your crops.” – Proverbs 3:9",
    "“For where your treasure is, there your heart will be also.” – Matthew 6:21",
    "“Whoever can be trusted with very little can also be trusted with much.” – Luke 16:10",
    "“It is required that those who have been given a trust must prove faithful.” – 1 Corinthians 4:2",
    "“The rich rule over the poor, and the borrower is slave to the lender.” – Proverbs 22:7",
    "“Bring the whole tithe into the storehouse, that there may be food in my house.” – Malachi 3:10",
    "“Keep your lives free from the love of money and be content with what you have.” – Hebrews 13:5",
    "“Command those who are rich in this present world not to be arrogant nor to put their hope in wealth, which is so uncertain, but to put their hope in God.” – 1 Timothy 6:17",
    "“But remember the Lord your God, for it is he who gives you the ability to produce wealth.” – Deuteronomy 8:18",
    "“Each of you should use whatever gift you have received to serve others, as faithful stewards of God’s grace in its various forms.” – 1 Peter 4:10",
    "“A good name is more desirable than great riches; to be esteemed is better than silver or gold.” – Proverbs 22:1",
    "“Whatever you do, work at it with all your heart, as working for the Lord, not for human masters.” – Colossians 3:23"
]

# --- HARDCODED DEFAULTS (2025 SIMPLIFIED) ---
DEFAULT_BUDGET = [
    {"Group": "Charity", "Category": "Tithes", "BudgetAmount": 0.0},
    {"Group": "Charity", "Category": "Giving", "BudgetAmount": 150.0},
    {"Group": "Charity", "Category": "SM savings", "BudgetAmount": 0.0},
    {"Group": "Savings", "Category": "HOUSE", "BudgetAmount": 0.0},
    {"Group": "Savings", "Category": "Car", "BudgetAmount": 0.0},
    {"Group": "Savings", "Category": "Dog", "BudgetAmount": 0.0},
    {"Group": "Housing", "Category": "Mortgage", "BudgetAmount": 1522.22},
    {"Group": "Housing", "Category": "Utilities", "BudgetAmount": 300.0},
    {"Group": "Housing", "Category": "Internet/TV", "BudgetAmount": 76.0},
    {"Group": "Housing", "Category": "Cellphone", "BudgetAmount": 50.0},
    {"Group": "Insurance", "Category": "Car Insurance", "BudgetAmount": 250.0},
    {"Group": "Transportation", "Category": "Gas", "BudgetAmount": 250.0},
    {"Group": "Transportation", "Category": "Car Maintenance", "BudgetAmount": 100.0},
    {"Group": "Food", "Category": "Groceries", "BudgetAmount": 700.0},
    {"Group": "Food", "Category": "Eating Out", "BudgetAmount": 300.0},
    {"Group": "Personal", "Category": "Pocket Money", "BudgetAmount": 200.0},
    {"Group": "Personal", "Category": "T Haircuts", "BudgetAmount": 30.0},
    {"Group": "Miscellaneous", "Category": "Gifts", "BudgetAmount": 100.0},
    {"Group": "Miscellaneous", "Category": "toiletries", "BudgetAmount": 100.0},
    {"Group": "Miscellaneous", "Category": "etc.", "BudgetAmount": 100.0},
    {"Group": "Miscellaneous", "Category": "Dates", "BudgetAmount": 100.0},
    {"Group": "Miscellaneous", "Category": "House", "BudgetAmount": 100.0},
    {"Group": "Miscellaneous", "Category": "Clothes", "BudgetAmount": 50.0},
    {"Group": "Medical", "Category": "Chiropractor", "BudgetAmount": 100.0},
    {"Group": "Medical", "Category": "Massage", "BudgetAmount": 144.0},
    {"Group": "Medical", "Category": "Medicine", "BudgetAmount": 50.0},
    {"Group": "Medical", "Category": "wellw/rae", "BudgetAmount": 0.0},
    {"Group": "Dog", "Category": "Dog Expenses", "BudgetAmount": 50.0},
    {"Group": "Baby", "Category": "Childcare", "BudgetAmount": 200.0}
]

DEFAULT_INCOME = [
    {"Source": "Tyler", "Amount": 6128.0},
    {"Source": "Mare", "Amount": 0.0}
]

# --- SMART BRAIN ---
SMART_DEFAULTS = {
    'heb': 'Groceries', 'walmart': 'Groceries', 'kroger': 'Groceries', 
    'aldi': 'Groceries', 'trader joe': 'Groceries', 'whole foods': 'Groceries',
    'costco': 'Groceries', 'sams club': 'Groceries', 'market street': 'Groceries',
    'mcdonalds': 'Eating Out', 'chick-fil-a': 'Eating Out', 
    'starbucks': 'Eating Out', 'burger king': 'Eating Out',
    'sonic': 'Eating Out', 'taco bell': 'Eating Out',
    'chipotle': 'Eating Out', 'whataburger': 'Eating Out',
    'panera': 'Eating Out', 'dunkin': 'Eating Out',
    'pizza': 'Eating Out', 'doordash': 'Eating Out',
    'uber eats': 'Eating Out', 'restaurant': 'Eating Out',
    'shell': 'Gas', 'exxon': 'Gas', 'chevron': 'Gas', 'texaco': 'Gas',
    '7-eleven': 'Gas', 'qt': 'Gas', 'quiktrip': 'Gas', 'buc-ee': 'Gas',
    'wawa': 'Gas', 'valero': 'Gas', 'pilot': 'Gas', 'circle k': 'Gas',
    'oil': 'Car Maintenance', 'auto': 'Car Maintenance', 'tire': 'Car Maintenance',
    'toyota': 'Car Maintenance', 'honda': 'Car Maintenance', 'mechanic': 'Car Maintenance',
    'att': 'Internet/TV', 'verizon': 'Cellphone', 't-mobile': 'Cellphone',
    'spectrum': 'Internet/TV', 'comcast': 'Internet/TV', 'xfinity': 'Internet/TV',
    'netflix': 'Internet/TV', 'hulu': 'Internet/TV', 'disney': 'Internet/TV',
    'spotify': 'Internet/TV', 'apple': 'Internet/TV', 'hbo': 'Internet/TV',
    'city of': 'Utilities', 'water': 'Utilities', 'electric': 'Utilities',
    'power': 'Utilities', 'energy': 'Utilities', 'waste': 'Utilities',
    'mortgage': 'Mortgage', 'loancare': 'Mortgage', 'mr cooper': 'Mortgage',
    'pharmacy': 'Medicine', 'cvs': 'Medicine', 'walgreens': 'Medicine',
    'doctor': 'Medicine', 'clinic': 'Medicine', 'health': 'Medicine',
    'chiropractor': 'Chiropractor', 'massage': 'Massage',
    'amazon': 'House', 'amzn': 'House', 'target': 'House', 
    'hair': 'T Haircuts', 'barber': 'T Haircuts', 'salon': 'T Haircuts',
    'pet': 'Dog Expenses', 'vet': 'Dog Expenses', 'dog': 'Dog Expenses',
    'chewy': 'Dog Expenses', 'daycare': 'Childcare', 'school': 'Childcare'
}

# --- PAGE SETUP ---
st.set_page_config(page_title="Stewardship App", page_icon="🌸", layout="wide")

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
    if st.button("Log In"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("Incorrect password")
    return False

# --- EMAILER ---
def send_email_report(subject, body_html):
    sender_email = st.secrets["EMAIL_SENDER"]
    sender_password = st.secrets["EMAIL_PASSWORD"]
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ", ".join(RECIPIENTS)
    msg['Subject'] = subject
    msg.attach(MIMEText(body_html, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, RECIPIENTS, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Email Failed: {e}")
        return False

# --- GITHUB MANAGER ---
class GithubManager:
    def __init__(self):
        try:
            self.g = Github(st.secrets["GITHUB_TOKEN"])
            self.repo = self.g.get_repo(st.secrets["REPO_NAME"])
        except Exception as e:
            st.error(f"GitHub Connection Error: {e}")

    def read_csv(self, file_key):
        path = FILE_PATHS[file_key]
        try:
            file_content = self.repo.get_contents(path, ref=BRANCH)
            decoded = file_content.decoded_content.decode("utf-8")
            if not decoded.strip(): return pd.DataFrame()
            return pd.read_csv(StringIO(decoded))
        except: return pd.DataFrame()

    def write_csv(self, df, file_key, message="Update data"):
        path = FILE_PATHS[file_key]
        csv_content = df.to_csv(index=False)
        try:
            file_content = self.repo.get_contents(path, ref=BRANCH)
            self.repo.update_file(path, message, csv_content, file_content.sha, branch=BRANCH)
            st.toast(f"Saved to GitHub ({file_key})! ☁️", icon="✅")
        except:
            try:
                self.repo.create_file(path, message, csv_content, branch=BRANCH)
                st.toast(f"Created new file ({file_key})! ☁️", icon="✅")
            except Exception as e: st.error(f"Save Error: {e}")

# --- LEARNING FUNCTION ---
def learn_keyword(manager, keyword, category):
    rules_df = manager.read_csv("budget_rules")
    if rules_df.empty: return False
    
    mask = rules_df['Category'] == category
    if not mask.any(): return False
    
    idx = rules_df[mask].index[0]
    
    current_kws = rules_df.at[idx, 'Keywords']
    try:
        kw_list = json.loads(current_kws) if pd.notna(current_kws) and current_kws else []
    except:
        kw_list = []
        
    clean_kw = keyword.lower().strip()
    if clean_kw not in kw_list:
        kw_list.append(clean_kw)
        rules_df.at[idx, 'Keywords'] = json.dumps(kw_list)
        manager.write_csv(rules_df, "budget_rules", f"Learned: {clean_kw} -> {category}")
        return True
    return False

def auto_categorize(df, rules):
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
            for keyword, category in SMART_DEFAULTS.items():
                if keyword in desc:
                    df.at[index, 'Category'] = category
                    break
        
        if "amazon" in desc or "amzn" in desc or "target" in desc:
            df.at[index, 'Nuance_Check'] = True
            
    return df

# --- HELPER: CLEAN CURRENCY ---
def clean_currency(df, col_name):
    if col_name in df.columns:
        df[col_name] = df[col_name].astype(str).str.replace(r'[$,]', '', regex=True)
        df[col_name] = pd.to_numeric(df[col_name], errors='coerce').fillna(0.0)
    return df

# --- SESSION STATE FOR DUPLICATES ---
if 'conflict_queue' not in st.session_state: st.session_state.conflict_queue = []
if 'processed_new_rows' not in st.session_state: st.session_state.processed_new_rows = []
if 'master_indices_to_drop' not in st.session_state: st.session_state.master_indices_to_drop = []

# --- DUPLICATE CHECKER LOGIC ---
def detect_duplicates(new_df, master_df):
    conflicts = []
    clean_rows = []
    
    if master_df.empty:
        return [], new_df.to_dict('records')

    # Convert dates to datetime for comparison
    master_df['DateObj'] = pd.to_datetime(master_df['Date'])
    
    for _, new_row in new_df.iterrows():
        new_date = pd.to_datetime(new_row['Date'])
        new_amt = float(new_row['Amount'])
        
        # 1. Exact Match Check (Date + Amt + Desc) - Auto Drop
        exact_match = master_df[
            (master_df['DateObj'] == new_date) & 
            (master_df['Amount'] == new_amt) & 
            (master_df['Description'] == new_row['Description'])
        ]
        
        if not exact_match.empty:
            continue # Skip silently (it's exactly the same)

        # 2. Fuzzy Match (Same Amt + Date +/- 2 days)
        date_min = new_date - timedelta(days=2)
        date_max = new_date + timedelta(days=2)
        
        fuzzy_match = master_df[
            (master_df['Amount'] == new_amt) & 
            (master_df['DateObj'] >= date_min) & 
            (master_df['DateObj'] <= date_max)
        ]
        
        if not fuzzy_match.empty:
            # Conflict found!
            existing_row = fuzzy_match.iloc[0] # Take the first match
            conflicts.append({
                'new': new_row.to_dict(),
                'existing': existing_row.to_dict(),
                'existing_idx': existing_row.name # The index in master_df
            })
        else:
            clean_rows.append(new_row.to_dict())
            
    return conflicts, clean_rows

# --- MAIN APP ---
if check_password():
    manager = GithubManager()
    
    # 1. Load Rules
    rules_df = manager.read_csv("budget_rules")
    rules_df = clean_currency(rules_df, "BudgetAmount")
    
    if rules_df.empty:
        st.info("Initializing Default Budget Rules...")
        rules_df = pd.DataFrame(DEFAULT_BUDGET)
        rules_df["Keywords"] = ""
        manager.write_csv(rules_df, "budget_rules", "Init 2025 Rules")
        time.sleep(1)
        st.rerun()
    
    categories = {}
    targets = {}
    custom_rules = {}
    for i, row in rules_df.iterrows():
        if pd.notna(row['Category']):
            categories[row['Category']] = row['Group']
            targets[row['Category']] = float(row['BudgetAmount'])
            if 'Keywords' in row and pd.notna(row['Keywords']) and row['Keywords']:
                try:
                    kws = json.loads(row['Keywords'])
                    for k in kws: custom_rules[k] = row['Category']
                except: pass

    # 2. Load Transactions
    tx_df = manager.read_csv("transactions")
    if tx_df.empty: tx_df = pd.DataFrame(columns=["Date", "Description", "Amount", "Category", "Is_Cru", "Nuance_Check"])
    tx_df = clean_currency(tx_df, "Amount")
    tx_df = tx_df.reset_index(drop=True)
    
    # 3. Load Income
    inc_df = manager.read_csv("income")
    inc_df = clean_currency(inc_df, "Amount")
    
    if inc_df.empty:
        inc_df = pd.DataFrame(DEFAULT_INCOME)
        manager.write_csv(inc_df, "income", "Init 2025 Income")

    # --- SIDEBAR ---
    st.sidebar.title("🌸 Menu")
    page = st.sidebar.radio("Go to:", ["🏠 Dashboard", "📥 Add Transactions", "🔄 Review & Edit", "💰 Income & Budget"])

    # --- DASHBOARD ---
    if page == "🏠 Dashboard":
        st.title("🌸 Stewardship Dashboard")
        
        # --- VERSE OF THE DAY ---
        st.markdown(f"> *{random.choice(STEWARDSHIP_VERSES)}*")
        st.divider()
        
        col_d1, col_d2 = st.columns([2, 1])
        with col_d1:
            if not tx_df.empty and 'Date' in tx_df.columns:
                tx_df['Date'] = pd.to_datetime(tx_df['Date'])
                today = datetime.now()
                first_day = today.replace(day=1)
                
                if 'date_range' not in st.session_state:
                    st.session_state.date_range = (first_day.date(), today.date())

                d_range = st.date_input("📅 Select Report Period (History Viewer)", 
                                      st.session_state.date_range)
                
                if len(d_range) == 2:
                    start_date, end_date = d_range
                    mask = (tx_df['Date'].dt.date >= start_date) & (tx_df['Date'].dt.date <= end_date)
                    dashboard_tx = tx_df[mask]
                    report_period = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
                else:
                    dashboard_tx = tx_df
                    report_period = "All Time"
            else:
                dashboard_tx = tx_df
                report_period = "No Data"

        personal_tx = dashboard_tx[dashboard_tx['Is_Cru'] == False] if not dashboard_tx.empty else dashboard_tx
        cru_tx = dashboard_tx[dashboard_tx['Is_Cru'] == True] if not dashboard_tx.empty else pd.DataFrame()

        total_income = float(inc_df['Amount'].sum()) if not inc_df.empty else 0.0
        total_spent = float(personal_tx['Amount'].sum()) if not personal_tx.empty else 0.0
        total_budget = sum(targets.values())
        
        if total_income > 0:
            savings_rate = ((total_income - total_spent) / total_income) * 100
        else:
            savings_rate = 0.0
        
        delta_val = total_budget - total_spent
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Income", f"${total_income:,.2f}")
        c2.metric("Total Budget", f"${total_budget:,.2f}")
        c3.metric("Actual Spent", f"${total_spent:,.2f}", delta=delta_val)
        
        st.progress(max(0, min(100, int(savings_rate))), text=f"Savings Rate: {savings_rate:.1f}%")

        with col_d2:
            st.write("") 
            if st.button("📧 Email This Report"):
                with st.spinner("Sending..."):
                    html = f"""
                    <h2>🌸 Stewardship Report: {report_period}</h2>
                    <p><b>Income:</b> ${total_income:,.2f}<br>
                    <b>Spent (Personal):</b> ${total_spent:,.2f}<br>
                    <b>Savings Rate:</b> {savings_rate:.1f}%</p>
                    <hr>
                    <h3>Category Breakdown</h3>
                    <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
                    <tr style="background-color: #D8BFD8;"><th>Category</th><th>Budget</th><th>Spent</th><th>Remaining</th></tr>
                    """
                    
                    actuals = personal_tx.groupby('Category')['Amount'].sum()
                    groups = {}
                    active_cats = set(targets.keys()) | set(actuals.index)
                    for c in active_cats:
                        g = categories.get(c, "Uncategorized")
                        if g not in groups: groups[g] = []
                        groups[g].append(c)
                    
                    for g in sorted(groups.keys()):
                        html += f"<tr><td colspan='4' style='background-color: #F0F0F0;'><b>{g}</b></td></tr>"
                        for cat in groups[g]:
                            b = targets.get(cat, 0.0)
                            s = actuals.get(cat, 0.0)
                            r = b - s
                            color = "red" if r < 0 else "green"
                            html += f"<tr><td>{cat}</td><td>${b:,.0f}</td><td>${s:,.0f}</td><td style='color:{color};'>${r:,.0f}</td></tr>"
                    
                    html += "</table>"

                    if not cru_tx.empty:
                        html += """
                        <br><hr>
                        <h3>🏢 Cru Reimbursables (To Submit)</h3>
                        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
                        <tr style="background-color: #FFD700;"><th>Date</th><th>Description</th><th>Amount</th></tr>
                        """
                        for idx, row in cru_tx.iterrows():
                            d_str = row['Date'].strftime('%Y-%m-%d') if pd.notna(row['Date']) else "N/A"
                            html += f"<tr><td>{d_str}</td><td>{row['Description']}</td><td>${row['Amount']:,.2f}</td></tr>"
                        html += "</table>"
                    else:
                        html += "<br><hr><p><i>No Cru expenses marked for this period.</i></p>"

                    html += "<br><p><i>Sent from your Stewardship App 🌸</i></p>"
                    
                    if send_email_report(f"Monthly Budget: {report_period}", html):
                        st.success("Sent to Tyler, Marianna, and Mare!")
                    else:
                        st.error("Check secrets configuration.")

        st.divider()
        st.subheader("🌿 Category Breakdown")
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
        
        # --- CONFLICT RESOLVER UI ---
        if st.session_state.conflict_queue:
            st.warning(f"⚠️ Potential Duplicate Found! ({len(st.session_state.conflict_queue)} remaining)")
            
            conflict = st.session_state.conflict_queue[0]
            existing = conflict['existing']
            new_item = conflict['new']
            
            c1, c2 = st.columns(2)
            with c1:
                st.info("🏛️ Existing Entry")
                st.markdown(f"**Date:** {existing['Date']}<br>**Desc:** {existing['Description']}<br>**Amt:** ${existing['Amount']}", unsafe_allow_html=True)
                if st.button("Keep Existing (Discard New)"):
                    st.session_state.conflict_queue.pop(0)
                    st.rerun()
                    
            with c2:
                st.success("🆕 New Entry")
                st.markdown(f"**Date:** {new_item['Date']}<br>**Desc:** {new_item['Description']}<br>**Amt:** ${new_item['Amount']}", unsafe_allow_html=True)
                if st.button("Replace with New"):
                    st.session_state.master_indices_to_drop.append(conflict['existing_idx'])
                    st.session_state.processed_new_rows.append(new_item)
                    st.session_state.conflict_queue.pop(0)
                    st.rerun()
            
            if st.button("Keep Both (They are different)"):
                st.session_state.processed_new_rows.append(new_item)
                st.session_state.conflict_queue.pop(0)
                st.rerun()
        
        # --- SAVING LOGIC ---
        elif st.session_state.processed_new_rows or st.session_state.master_indices_to_drop:
            with st.spinner("Finalizing changes..."):
                if st.session_state.master_indices_to_drop:
                    tx_df = tx_df.drop(st.session_state.master_indices_to_drop)
                
                if st.session_state.processed_new_rows:
                    new_data_df = pd.DataFrame(st.session_state.processed_new_rows)
                    tx_df = pd.concat([tx_df, new_data_df], ignore_index=True)
                
                tx_df['Date'] = pd.to_datetime(tx_df['Date'])
                tx_df = tx_df.sort_values(by="Date", ascending=False)
                tx_df['Date'] = tx_df['Date'].dt.strftime('%Y-%m-%d')
                
                manager.write_csv(tx_df, "transactions", "Batch Upload with De-Duping")
                
                st.session_state.conflict_queue = []
                st.session_state.processed_new_rows = []
                st.session_state.master_indices_to_drop = []
                
                st.success("All transactions processed and saved!")
                time.sleep(2)
                st.rerun()

        # --- NORMAL TABS ---
        else:
            tab_manual, tab_csv, tab_split = st.tabs(["✍️ Manual Entry", "📂 Bulk Upload", "✂️ Split Transaction"])
            
            with tab_manual:
                all_cats = sorted(list(categories.keys()))
                sel_cat = st.selectbox("Category", all_cats, index=0) if all_cats else None
                
                if sel_cat:
                    b_val = targets.get(sel_cat, 0.0)
                    if not tx_df.empty:
                        tx_df['Is_Cru'] = tx_df['Is_Cru'].astype(bool)
                        curr_s = tx_df[(tx_df['Category'] == sel_cat) & (tx_df['Is_Cru'] == False)]['Amount'].sum()
                    else: curr_s = 0.0
                    rem_val = b_val - curr_s
                    
                    c1, c2 = st.columns(2)
                    c1.metric(f"Budget: {sel_cat}", f"${b_val:,.0f}")
                    c2.metric(f"Available", f"${rem_val:,.2f}", delta_color="normal" if rem_val > 0 else "inverse")

                c1, c2 = st.columns(2)
                d_date = c1.date_input("Date", datetime.now())
                d_amt = c2.number_input("Amount ($)", min_value=0.0, step=0.01)
                d_desc = st.text_input("Description", placeholder="e.g. HEB")
                is_cru = st.checkbox("Is this a Cru Expense?")
                remember = st.checkbox(f"🧠 Remember that '{d_desc}' is always '{sel_cat}'?")
                
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
                        
                        conflicts, clean = detect_duplicates(new_row, tx_df)
                        
                        if conflicts:
                            st.session_state.conflict_queue = conflicts
                            st.session_state.processed_new_rows = []
                            st.rerun()
                        else:
                            updated_df = pd.concat([tx_df, new_row], ignore_index=True)
                            manager.write_csv(updated_df, "transactions", "Add Manual Transaction")
                            if remember and d_desc:
                                learn_keyword(manager, d_desc, sel_cat)
                            st.success("Added!"); time.sleep(1); st.rerun()

            with tab_csv:
                uploaded_files = st.file_uploader("Choose CSV files", accept_multiple_files=True, type='csv')
                if st.button("Process CSVs"):
                    if uploaded_files:
                        all_new_rows = []
                        for f in uploaded_files:
                            try:
                                temp = pd.read_csv(f, header=None)
                                if len(temp.columns) < 5: temp = pd.read_csv(f)
                                if 'Description' not in temp.columns:
                                    temp = temp.rename(columns={0: 'Date', 1: 'Amount', 4: 'Description'})
                                
                                temp['Amount'] = temp['Amount'].astype(str).str.replace(r'[$,]', '', regex=True)
                                temp['Amount'] = pd.to_numeric(temp['Amount'], errors='coerce')
                                temp = temp.dropna(subset=['Amount'])
                                if (temp['Amount'] < 0).any(): temp['Amount'] = temp['Amount'] * -1
                                else: temp['Amount'] = temp['Amount'].abs()
                                temp['Category'] = None; temp['Is_Cru'] = False; temp['Nuance_Check'] = False
                                
                                temp = auto_categorize(temp, custom_rules)
                                all_new_rows.append(temp)
                            except Exception as e: st.error(f"Error {f.name}: {e}")
                        
                        if all_new_rows:
                            big_new_df = pd.concat(all_new_rows, ignore_index=True)
                            big_new_df['Date'] = pd.to_datetime(big_new_df['Date']).dt.strftime('%Y-%m-%d')
                            
                            conflicts, clean_rows = detect_duplicates(big_new_df, tx_df)
                            
                            st.session_state.conflict_queue = conflicts
                            st.session_state.processed_new_rows = clean_rows
                            st.rerun()

            with tab_split:
                st.info("Split a large transaction into multiple categories.")
                if tx_df.empty:
                    st.warning("No transactions available to split.")
                else:
                    tx_df = tx_df.sort_values(by="Date", ascending=False)
                    tx_df['label'] = tx_df.apply(lambda x: f"{x['Date']} | {x['Description']} | ${x['Amount']}", axis=1)
                    selected_label = st.selectbox("Select Transaction to Split", tx_df['label'].unique())
                    
                    original_row = tx_df[tx_df['label'] == selected_label].iloc[0]
                    orig_amt = float(original_row['Amount'])
                    st.markdown(f"**Original Amount:** `${orig_amt:,.2f}`")
                    
                    num_splits = st.radio("Split into how many?", [2, 3, 4], horizontal=True)
                    splits = []
                    running_total = 0.0
                    
                    for i in range(num_splits):
                        c1, c2 = st.columns([1, 2])
                        val = c1.number_input(f"Amount {i+1}", min_value=0.0, step=0.01, key=f"s_amt_{i}")
                        cat = c2.selectbox(f"Category {i+1}", all_cats, key=f"s_cat_{i}")
                        splits.append({"amount": val, "category": cat})
                        running_total += val
                    
                    remaining = orig_amt - running_total
                    if abs(remaining) < 0.01:
                        st.success("✅ Math matches! Ready to split.")
                        if st.button("✂️ Process Split"):
                            mask = (tx_df['Date'] == original_row['Date']) & \
                                   (tx_df['Description'] == original_row['Description']) & \
                                   (tx_df['Amount'] == original_row['Amount'])
                            idx_to_drop = tx_df[mask].index[0]
                            new_tx_df = tx_df.drop(idx_to_drop).drop(columns=['label'])
                            
                            new_rows = []
                            for s in splits:
                                new_rows.append({
                                    "Date": original_row['Date'],
                                    "Description": f"{original_row['Description']} (Split)",
                                    "Amount": s['amount'],
                                    "Category": s['category'],
                                    "Is_Cru": original_row['Is_Cru'],
                                    "Nuance_Check": False
                                })
                            
                            new_tx_df = pd.concat([new_tx_df, pd.DataFrame(new_rows)], ignore_index=True)
                            manager.write_csv(new_tx_df, "transactions", f"Split {original_row['Description']}")
                            st.success("Transaction Split!"); time.sleep(1); st.rerun()
                    else:
                        st.error(f"❌ Amounts do not match. Remaining: ${remaining:,.2f}")

    # --- REVIEW ---
    elif page == "🔄 Review & Edit":
        st.header("📝 Review Transactions")
        
        with st.expander("🧠 Train the Brain (Teach it new rules)"):
            c_learn1, c_learn2, c_learn3 = st.columns([2, 2, 1])
            learn_kw = c_learn1.text_input("If description contains...", placeholder="e.g. Netflix")
            learn_cat = c_learn2.selectbox("Always assign to:", sorted(list(categories.keys())))
            if c_learn3.button("Teach"):
                if learn_kw:
                    if learn_keyword(manager, learn_kw, learn_cat):
                        st.success(f"Learned! Future '{learn_kw}' will be '{learn_cat}'.")
                        time.sleep(1); st.rerun()
                    else: st.error("Could not update rules.")
        
        st.divider()
        
        c_view1, c_view2, c_view3 = st.columns([2, 1, 1])
        view_mode = c_view1.radio("Show:", ["Needs Review", "All Transactions"], horizontal=True)
        sort_col = c_view2.selectbox("Sort by:", ["Date", "Amount", "Category", "Description"], index=0)
        sort_order = c_view3.radio("Order:", ["Newest/Highest", "Oldest/Lowest"], horizontal=True)
        ascending = True if sort_order == "Oldest/Lowest" else False

        if 'Date' in tx_df.columns: tx_df['Date'] = pd.to_datetime(tx_df['Date'])
        
        mask = (tx_df['Category'].isnull()) | (tx_df['Nuance_Check'] == True)
        edit_view = tx_df[mask].copy() if view_mode == "Needs Review" else tx_df.copy()
        
        if not edit_view.empty:
            edit_view = edit_view.sort_values(by=sort_col, ascending=ascending)
            
        if edit_view.empty: st.success("Nothing to review!")
        else:
            cat_options = sorted(list(categories.keys())); cat_options.insert(0, "Business/Cru")
            
            edited_view = st.data_editor(
                edit_view, 
                column_config={
                    "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                    "Category": st.column_config.SelectboxColumn("Category", options=cat_options),
                    "Is_Cru": st.column_config.CheckboxColumn("Cru Expense"),
                    "Nuance_Check": st.column_config.CheckboxColumn("Review Needed"),
                    "Amount": st.column_config.NumberColumn("Amount", format="$%.2f")
                }, 
                use_container_width=True, 
                num_rows="dynamic"
            )
            
            if st.button("Save Changes"):
                indices_shown = edit_view.index
                remaining_df = tx_df.drop(indices_shown)
                final_df = pd.concat([remaining_df, edited_view], ignore_index=False)
                final_df['Date'] = final_df['Date'].dt.strftime('%Y-%m-%d')
                final_df = final_df.sort_values(by="Date", ascending=False)
                manager.write_csv(final_df, "transactions", "Review Changes")
                st.success("Saved!"); time.sleep(1); st.rerun()

    # --- SETTINGS ---
    elif page == "💰 Income & Budget":
        st.header("Settings")
        t1, t2 = st.tabs(["Income", "Budget Categories"])
        with t1:
            edited_inc = st.data_editor(inc_df, num_rows="dynamic", use_container_width=True)
            if st.button("Save Income"): manager.write_csv(edited_inc, "income", "Update Income")
        with t2:
            st.info("Edit your budget targets here.")
            
            # --- THE CONSOLIDATOR ---
            st.markdown("---")
            st.subheader("✨ Consolidate Categories")
            st.caption("One-click fix to rename all 'Eating out Together/Separate' to 'Eating Out', and 'Pocket Money His/Her' to 'Pocket Money'.")
            
            if st.button("✨ Consolidate Categories"):
                new_rules = pd.DataFrame(DEFAULT_BUDGET)
                new_rules["Keywords"] = ""
                manager.write_csv(new_rules, "budget_rules", "Consolidate Rules")
                
                changes = {
                    "Eating out together": "Eating Out",
                    "Eating out seperate": "Eating Out",
                    "Eating Out His": "Eating Out",
                    "Eating Out Hers": "Eating Out",
                    "Pocket Money his": "Pocket Money",
                    "Pocket Money her": "Pocket Money",
                    "Pocket Money His": "Pocket Money",
                    "Pocket Money Hers": "Pocket Money"
                }
                
                count = 0
                for old, new in changes.items():
                    mask = tx_df['Category'] == old
                    if mask.any():
                        tx_df.loc[mask, 'Category'] = new
                        count += mask.sum()
                
                if count > 0:
                    manager.write_csv(tx_df, "transactions", "Consolidate Transactions")
                    st.success(f"Updated {count} transactions and rules!"); time.sleep(2); st.rerun()
                else:
                    st.info("Rules updated, but no matching transactions found to rename.")
            st.markdown("---")

            st.markdown("---")
            st.subheader("🛠️ Bulk Rename Tool")
            if not tx_df.empty:
                current_used_cats = [str(x) for x in tx_df['Category'].unique() if pd.notna(x)]
                current_used_cats.sort()
                valid_cats = sorted(list(categories.keys()))
                
                col_mig1, col_mig2, col_mig3 = st.columns([2, 2, 1])
                old_cat_input = col_mig1.selectbox("Find all transactions labeled:", current_used_cats)
                new_cat_input = col_mig2.selectbox("And rename them to:", valid_cats)
                
                if col_mig3.button("Rename"):
                    count = len(tx_df[tx_df['Category'] == old_cat_input])
                    if count > 0:
                        tx_df.loc[tx_df['Category'] == old_cat_input, 'Category'] = new_cat_input
                        manager.write_csv(tx_df, "transactions", f"Migrate {old_cat_input} -> {new_cat_input}")
                        st.success(f"Moved {count} transactions!"); time.sleep(1); st.rerun()
                    else:
                        st.warning("No transactions found with that category.")
            st.markdown("---")

            st.markdown("---")
            col_warn, col_btn = st.columns([3, 1])
            col_warn.warning("Click here if you need to force-load the new 2025 Budget Categories.")
            if col_btn.button("⚠️ Reset to 2025 Defaults"):
                 new_rules = pd.DataFrame(DEFAULT_BUDGET)
                 new_rules["Keywords"] = ""
                 manager.write_csv(new_rules, "budget_rules", "Force Reset to 2025 Defaults")
                 time.sleep(1)
                 st.rerun()
            st.markdown("---")
            
            edited_rules = st.data_editor(rules_df[['Category', 'Group', 'BudgetAmount']], num_rows="dynamic", use_container_width=True)
            if st.button("Save Categories"): manager.write_csv(edited_rules, "budget_rules", "Update Rules")
