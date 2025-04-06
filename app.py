import streamlit as st
import datetime
import json
import pandas as pd
import hashlib
import platform

# Set page configuration
st.set_page_config(
    page_title="Year 11 Committee Financial System",
    page_icon="💰",
    layout="wide"
)

# Add custom CSS for responsiveness
st.markdown("""
<style>
    /* Improve general responsiveness */
    .stApp {
        max-width: 100%;
    }
    
    /* Make text responsive */
    h1, h2, h3 {
        margin-top: 0;
    }
    
    /* Improve form input fields */
    div[data-baseweb="input"], div[data-baseweb="textarea"] {
        width: 100%;
    }
    
    /* Make dataframes scroll horizontally on small screens */
    .stDataFrame {
        overflow-x: auto;
    }
    
    /* Improve button layout */
    .stButton > button {
        width: 100%;
    }
    
    /* Adjust metrics for mobile */
    @media screen and (max-width: 640px) {
        [data-testid="stMetricValue"] {
            font-size: 1.1rem !important;
        }
        [data-testid="stMetricDelta"] {
            font-size: 0.8rem !important;
        }
        .st-emotion-cache-u8hs99 {
            flex-direction: column !important;
        }
    }
    
    /* Fix sidebar on small screens */
    @media screen and (max-width: 768px) {
        .st-emotion-cache-z5fcl4 {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
    }
    
    /* Improve form layout */
    .responsive-form .st-emotion-cache-ocqkz7 {
        flex-direction: column !important;
    }
    
    /* Make columns stack on mobile */
    @media screen and (max-width: 768px) {
        .mobile-stack {
            flex-direction: column !important;
        }
        .mobile-stack > div {
            width: 100% !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Password configuration
# These would ideally be stored more securely in a production environment
def check_credentials(username, password, user_credentials):
    """Check if username and password match stored credentials"""
    if username in user_credentials:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        return hashed_password == user_credentials[username]["password_hash"]
    return False

def get_user_role(username, user_credentials):
    """Get the role for a username"""
    if username in user_credentials:
        return user_credentials[username]["role"]
    return None

# User credentials - in a real app, this would be stored more securely
# Format: {"username": {"password_hash": "hash_value", "role": "admin or viewer"}}
USER_CREDENTIALS = {
    "admin": {
        "password_hash": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",  # "password"
        "role": "admin"
    },
    "viewer": {
        "password_hash": "d35ca5051b82ffc326a3b0b6574a9a3161dee16b9478a199ee39cd803ce5b799",  # "viewer"
        "role": "viewer"
    }
}

# Detect device type for responsive design
def get_device_type():
    user_agent = platform.system()
    # This is a simple detection that could be enhanced with browser user agent analysis
    if 'mobile' in user_agent.lower() or 'android' in user_agent.lower() or 'ios' in user_agent.lower():
        return "mobile"
    elif 'tablet' in user_agent.lower() or 'ipad' in user_agent.lower():
        return "tablet"
    else:
        return "desktop"

# Initialize session state variables if they don't exist
if 'device_type' not in st.session_state:
    st.session_state.device_type = get_device_type()

if 'transactions' not in st.session_state:
    st.session_state.transactions = []

if 'budget' not in st.session_state:
    st.session_state.budget = {
        "income": {
            "Fundraising Events": {"budget": 0, "actual": 0},
            "Merchandise Sales": {"budget": 0, "actual": 0},
            "Sponsorships": {"budget": 0, "actual": 0},
            "Other Income": {"budget": 0, "actual": 0}
        },
        "expenses": {
            "Event Expenses": {"budget": 0, "actual": 0},
            "Merchandise Production": {"budget": 0, "actual": 0},
            "Marketing/Promotion": {"budget": 0, "actual": 0},
            "Yearbook": {"budget": 0, "actual": 0},
            "Graduation": {"budget": 0, "actual": 0},
            "School Trips": {"budget": 0, "actual": 0},
            "Emergency Reserve": {"budget": 0, "actual": 0},
            "Other Expenses": {"budget": 0, "actual": 0}
        }
    }

if 'events' not in st.session_state:
    st.session_state.events = []

if 'fundraising' not in st.session_state:
    st.session_state.fundraising = []

# Authentication state variables
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'user_role' not in st.session_state:
    st.session_state.user_role = None

if 'username' not in st.session_state:
    st.session_state.username = None

# Committee members
committee_members = {
    "Chair": "TBD",
    "Deputy Chair": "TBD",
    "Treasurer": "Deema Abououf",
    "Secretary": "TBD",
    "Events Coordinator": "TBD"
}

# Authorization levels based on the matrix
auth_levels = {
    "Under 100 KD": ["Chair"],
    "Over 100 KD": ["Chair", "School Admin"],
    "New Category": ["Committee Vote"]
}

# Helper functions
def get_balance():
    total_income = sum(t["income"] for t in st.session_state.transactions)
    total_expenses = sum(t["expense"] for t in st.session_state.transactions)
    return total_income - total_expenses

def get_emergency_reserve():
    # Calculate 15% of total income
    total_income = sum(t["income"] for t in st.session_state.transactions)
    return total_income * 0.15

def get_required_authorization(amount, category):
    # Check if this is a new category
    is_new_category = True
    for section in ["income", "expenses"]:
        if category in st.session_state.budget[section]:
            is_new_category = False
            break
    
    if is_new_category:
        return ["Committee Vote"]
    elif float(amount) > 100:
        return auth_levels["Over 100 KD"]
    else:
        return auth_levels["Under 100 KD"]

def add_transaction(date, description, category, income=0, expense=0, authorized_by="", receipt_num="", notes=""):
    # Validate transaction
    if not description or not category:
        return False, "Description and category are required"
    
    # Check authorization based on amount
    amount = max(income, expense)
    required_auth = get_required_authorization(amount, category)
    if authorized_by not in required_auth and "Committee Vote" not in required_auth:
        return False, f"This transaction requires authorization from: {', '.join(required_auth)}"
    
    # Add transaction
    transaction = {
        "date": date,
        "description": description,
        "category": category,
        "income": float(income),
        "expense": float(expense),
        "authorized_by": authorized_by,
        "receipt_num": receipt_num,
        "notes": notes,
        "timestamp": datetime.datetime.now().isoformat()
    }
    st.session_state.transactions.append(transaction)
    
    # Update budget actuals
    if income > 0:
        if category in st.session_state.budget["income"]:
            st.session_state.budget["income"][category]["actual"] += float(income)
        else:
            st.session_state.budget["income"]["Other Income"]["actual"] += float(income)
    
    if expense > 0:
        if category in st.session_state.budget["expenses"]:
            st.session_state.budget["expenses"][category]["actual"] += float(expense)
        else:
            st.session_state.budget["expenses"]["Other Expenses"]["actual"] += float(expense)
    
    return True, "Transaction added successfully"

def generate_monthly_report(month=None, year=None):
    now = datetime.datetime.now()
    month = month or now.month
    year = year or now.year
    
    # Filter transactions for the given month/year
    monthly_transactions = []
    for t in st.session_state.transactions:
        try:
            t_date = datetime.datetime.fromisoformat(t["timestamp"]).date()
            if t_date.month == month and t_date.year == year:
                monthly_transactions.append(t)
        except (ValueError, KeyError):
            continue
    
    monthly_income = sum(t["income"] for t in monthly_transactions)
    monthly_expenses = sum(t["expense"] for t in monthly_transactions)
    
    report = {
        "month": month,
        "year": year,
        "total_income": monthly_income,
        "total_expenses": monthly_expenses,
        "net": monthly_income - monthly_expenses,
        "transactions": monthly_transactions,
        "current_balance": get_balance(),
        "emergency_reserve": get_emergency_reserve(),
        "available_funds": get_balance() - get_emergency_reserve()
    }
    
    return report

def create_event_budget(event_name, date, location, coordinator, projected_income=0, projected_expenses=0):
    event = {
        "name": event_name,
        "date": date,
        "location": location,
        "coordinator": coordinator,
        "projected_income": float(projected_income),
        "projected_expenses": float(projected_expenses),
        "actual_income": 0,
        "actual_expenses": 0,
        "income_sources": [],
        "expense_items": [],
        "status": "Planning"  # Planning, Active, Completed
    }
    
    st.session_state.events.append(event)
    return True, "Event budget created successfully"

def add_fundraising_initiative(name, dates, coordinator, goal_amount):
    initiative = {
        "name": name,
        "dates": dates,
        "coordinator": coordinator,
        "goal_amount": float(goal_amount),
        "actual_raised": 0,
        "expenses": 0,
        "net_proceeds": 0,
        "status": "Planning"  # Planning, Active, Completed
    }
    
    st.session_state.fundraising.append(initiative)
    return True, "Fundraising initiative added successfully"

# Login screen function
def show_login():
    st.title("Year 11 Committee Financial System")
    st.subheader("Login")
    
    # Center the login form on larger screens
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Create a login form
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
            
            if submitted:
                if check_credentials(username, password, USER_CREDENTIALS):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.user_role = get_user_role(username, USER_CREDENTIALS)
                    st.success(f"Login successful! Welcome {username}.")
                    st.rerun()
                else:
                    st.error("Incorrect username or password. Please try again.")
    
    # Instructions for users
    with col2:
        st.markdown("---")
        st.markdown("""
        ### Access Levels:
        - **Admin:** Full access to all features
        - **Viewer:** View dashboard and generate reports only
        
        Please enter your username and password to login.
        
        Default accounts:
        - Username: admin (full access)
        - Username: viewer (view-only access)
        """)

# Dashboard function
def show_dashboard():
    st.header("Financial Dashboard")
    
    # Summary cards in a row
    # Use the mobile-stack class for responsive columns
    cols_div = '<div class="mobile-stack">'
    st.markdown(cols_div, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    balance = get_balance()
    reserve = get_emergency_reserve()
    available = balance - reserve
    
    with col1:
        st.metric("Current Balance", f"KD {balance:.2f}")
    
    with col2:
        st.metric("Emergency Reserve (15%)", f"KD {reserve:.2f}")
    
    with col3:
        st.metric("Available Funds", f"KD {available:.2f}")
    
    # Recent transactions
    st.subheader("Recent Transactions")
    
    if st.session_state.transactions:
        transactions_df = pd.DataFrame(st.session_state.transactions)
        # Sort by timestamp (newest first)
        if "timestamp" in transactions_df.columns:
            transactions_df = transactions_df.sort_values(by="timestamp", ascending=False)
        # Limit to last 5
        recent_transactions = transactions_df.head(5)
        # Select only the columns we want to display
        display_columns = [col for col in ["date", "description", "category", "income", "expense", "authorized_by"] 
                           if col in recent_transactions.columns]
        st.dataframe(recent_transactions[display_columns], use_container_width=True)
    else:
        st.info("No transactions recorded yet.")
    
    # Budget overview with tables
    st.subheader("Budget Overview")
    
    # Use the mobile-stack class for responsive columns
    cols_div = '<div class="mobile-stack">'
    st.markdown(cols_div, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Income budget vs actual
        st.write("**Income: Budget vs. Actual**")
        income_data = []
        for category, values in st.session_state.budget["income"].items():
            income_data.append({
                "Category": category,
                "Budget": f"KD {values['budget']:.2f}",
                "Actual": f"KD {values['actual']:.2f}",
                "Variance": f"KD {values['actual'] - values['budget']:.2f}"
            })
        
        if income_data:
            income_df = pd.DataFrame(income_data)
            st.dataframe(income_df, use_container_width=True)
    
    with col2:
        # Expense budget vs actual
        st.write("**Expenses: Budget vs. Actual**")
        expense_data = []
        for category, values in st.session_state.budget["expenses"].items():
            expense_data.append({
                "Category": category,
                "Budget": f"KD {values['budget']:.2f}",
                "Actual": f"KD {values['actual']:.2f}",
                "Variance": f"KD {values['actual'] - values['budget']:.2f}"
            })
        
        if expense_data:
            expense_df = pd.DataFrame(expense_data)
            st.dataframe(expense_df, use_container_width=True)
    
    # Close the mobile-stack div
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Quick actions (shown only to admin users)
    if st.session_state.user_role == "admin":
        st.subheader("Quick Actions")
        
        # Use the mobile-stack class for responsive columns
        cols_div = '<div class="mobile-stack">'
        st.markdown(cols_div, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Add Transaction", use_container_width=True):
                st.session_state.page = "transactions"
        
        with col2:
            if st.button("Generate Report", use_container_width=True):
                st.session_state.page = "reports"
        
        with col3:
            if st.button("Manage Budget", use_container_width=True):
                st.session_state.page = "budget"
        
        # Close the mobile-stack div
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # For viewer role, only show report generation button
        st.subheader("Quick Actions")
        if st.button("Generate Report", use_container_width=True):
            st.session_state.page = "reports"

# Transactions function
def show_transactions():
    st.header("Transactions Management")
    
    # Add new transaction form
    with st.expander("Add New Transaction", expanded=True):
        # Add the responsive-form class
        st.markdown('<div class="responsive-form">', unsafe_allow_html=True)
        
        with st.form("transaction_form"):
            # Use the mobile-stack class for responsive columns
            cols_div = '<div class="mobile-stack">'
            st.markdown(cols_div, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                date = st.date_input("Date", value=datetime.date.today())
                description = st.text_input("Description")
                
                # Get all categories
                categories = list(st.session_state.budget["income"].keys()) + list(st.session_state.budget["expenses"].keys())
                category = st.selectbox("Category", categories)
                
                income = st.number_input("Income (KD)", min_value=0.0, format="%.2f")
            
            with col2:
                expense = st.number_input("Expense (KD)", min_value=0.0, format="%.2f")
                
                # Get all possible authorizers
                authorizers = list(committee_members.keys()) + ["School Admin", "Committee Vote"]
                authorized_by = st.selectbox("Authorized By", authorizers)
                
                receipt_num = st.text_input("Receipt #")
                notes = st.text_area("Notes", height=100)
            
            # Close the mobile-stack div
            st.markdown('</div>', unsafe_allow_html=True)
            
            submit = st.form_submit_button("Add Transaction", use_container_width=True)
            
            if submit:
                success, message = add_transaction(
                    date.strftime("%Y-%m-%d"),
                    description,
                    category,
                    income,
                    expense,
                    authorized_by,
                    receipt_num,
                    notes
                )
                
                if success:
                    st.success(message)
                else:
                    st.error(message)
        
        # Close the responsive-form div
        st.markdown('</div>', unsafe_allow_html=True)
    
    # View transactions
    st.subheader("Transaction History")
    
    if st.session_state.transactions:
        transactions_df = pd.DataFrame(st.session_state.transactions)
        # Sort by date (newest first)
        if "timestamp" in transactions_df.columns:
            transactions_df = transactions_df.sort_values(by="timestamp", ascending=False)
        # Format currency columns
        if "income" in transactions_df.columns:
            transactions_df["income"] = transactions_df["income"].apply(lambda x: f"KD {x:.2f}" if x > 0 else "")
        if "expense" in transactions_df.columns:
            transactions_df["expense"] = transactions_df["expense"].apply(lambda x: f"KD {x:.2f}" if x > 0 else "")
        # Select columns to display
        display_columns = [col for col in ["date", "description", "category", "income", "expense", "authorized_by", "receipt_num", "notes"]
                           if col in transactions_df.columns]
        st.dataframe(transactions_df[display_columns], use_container_width=True)
        
        # Export option
        if st.button("Export Transactions to CSV", use_container_width=True):
            csv = transactions_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="transactions.csv",
                mime="text/csv",
                use_container_width=True
            )
    else:
        st.info("No transactions recorded yet.")

# Budget function
def show_budget():
    st.header("Budget Management")
    
    # Add new budget category
    with st.expander("Add New Budget Category"):
        # Add the responsive-form class
        st.markdown('<div class="responsive-form">', unsafe_allow_html=True)
        
        with st.form("new_category_form"):
            # Use the mobile-stack class for responsive columns
            cols_div = '<div class="mobile-stack">'
            st.markdown(cols_div, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                category_name = st.text_input("Category Name")
                category_type = st.radio("Category Type", ["Income", "Expenses"])
            
            with col2:
                initial_budget = st.number_input("Initial Budget (KD)", min_value=0.0, format="%.2f")
            
            # Close the mobile-stack div
            st.markdown('</div>', unsafe_allow_html=True)
            
            submit = st.form_submit_button("Add Category", use_container_width=True)
            
            if submit:
                if not category_name:
                    st.error("Category name is required")
                else:
                    category_type = category_type.lower()
                    if category_type == "income":
                        if category_name in st.session_state.budget["income"]:
                            st.error(f"Category '{category_name}' already exists in income categories")
                        else:
                            st.session_state.budget["income"][category_name] = {"budget": initial_budget, "actual": 0}
                            st.success(f"Added '{category_name}' to income categories")
                    else:
                        if category_name in st.session_state.budget["expenses"]:
                            st.error(f"Category '{category_name}' already exists in expense categories")
                        else:
                            st.session_state.budget["expenses"][category_name] = {"budget": initial_budget, "actual": 0}
                            st.success(f"Added '{category_name}' to expense categories")
        
        # Close the responsive-form div
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Adjust existing budget categories
    with st.expander("Adjust Budget Amounts"):
        st.subheader("Income Categories")
        
        # Make the budget adjustment layout responsive
        st.markdown('<div class="responsive-budget">', unsafe_allow_html=True)
        
        for category, values in st.session_state.budget["income"].items():
            # Use the mobile-stack class for responsive columns on small screens
            cols_div = '<div class="mobile-stack">'
            st.markdown(cols_div, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([3, 2, 2])
            
            with col1:
                st.text(category)
            
            with col2:
                current_budget = values["budget"]
                st.text(f"Current: KD {current_budget:.2f}")
            
            with col3:
                new_budget = st.number_input(f"New budget for {category}", 
                                            min_value=0.0, 
                                            value=float(current_budget),
                                            key=f"income_{category}",
                                            format="%.2f")
                if new_budget != current_budget:
                    st.session_state.budget["income"][category]["budget"] = new_budget
            
            # Close the mobile-stack div
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.subheader("Expense Categories")
        
        for category, values in st.session_state.budget["expenses"].items():
            # Use the mobile-stack class for responsive columns on small screens
            cols_div = '<div class="mobile-stack">'
            st.markdown(cols_div, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([3, 2, 2])
            
            with col1:
                st.text(category)
            
            with col2:
                current_budget = values["budget"]
                st.text(f"Current: KD {current_budget:.2f}")
            
            with col3:
                new_budget = st.number_input(f"New budget for {category}", 
                                            min_value=0.0, 
                                            value=float(current_budget),
                                            key=f"expense_{category}",
                                            format="%.2f")
                if new_budget != current_budget:
                    st.session_state.budget["expenses"][category]["budget"] = new_budget
            
            # Close the mobile-stack div
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Close the responsive-budget div
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Budget overview
    st.subheader("Budget Summary")
    
    # Calculate totals
    total_income_budget = sum(values["budget"] for values in st.session_state.budget["income"].values())
    total_income_actual = sum(values["actual"] for values in st.session_state.budget["income"].values())
    total_expense_budget = sum(values["budget"] for values in st.session_state.budget["expenses"].values())
    total_expense_actual = sum(values["actual"] for values in st.session_state.budget["expenses"].values())
    
    # Display summary metrics
    # Use the mobile-stack class for responsive columns
    cols_div = '<div class="mobile-stack">'
    st.markdown(cols_div, unsafe_allow_html=True)
    
    # Use 2x2 grid for mobile and 4x1 for desktop
    if st.session_state.device_type == "mobile":
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Income Budget", f"KD {total_income_budget:.2f}")
        with col2:
            st.metric("Income Actual", f"KD {total_income_actual:.2f}", 
                    f"{(total_income_actual - total_income_budget):.2f}")
        
        col3, col4 = st.columns(2)
        with col3:
            st.metric("Expense Budget", f"KD {total_expense_budget:.2f}")
        with col4:
            st.metric("Expense Actual", f"KD {total_expense_actual:.2f}", 
                    f"{(total_expense_actual - total_expense_budget):.2f}")
    else:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Income Budget", f"KD {total_income_budget:.2f}")
        
        with col2:
            st.metric("Total Income Actual", f"KD {total_income_actual:.2f}", 
                    f"{(total_income_actual - total_income_budget):.2f}")
        
        with col3:
            st.metric("Total Expense Budget", f"KD {total_expense_budget:.2f}")
        
        with col4:
            st.metric("Total Expense Actual", f"KD {total_expense_actual:.2f}", 
                    f"{(total_expense_actual - total_expense_budget):.2f}")
    
    # Close the mobile-stack div
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Budget tables
    # Use the mobile-stack class for responsive columns
    cols_div = '<div class="mobile-stack">'
    st.markdown(cols_div, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Income Budget")
        
        income_data = []
        for category, values in st.session_state.budget["income"].items():
            income_data.append({
                "Category": category,
                "Budget": f"KD {values['budget']:.2f}",
                "Actual": f"KD {values['actual']:.2f}",
                "Variance": f"KD {values['actual'] - values['budget']:.2f}",
                "% of Budget": f"{(values['actual'] / values['budget'] * 100):.1f}%" if values['budget'] > 0 else "N/A"
            })
        
        if income_data:
            income_df = pd.DataFrame(income_data)
            st.dataframe(income_df, use_container_width=True)
    
    with col2:
        st.subheader("Expense Budget")
        
        expense_data = []
        for category, values in st.session_state.budget["expenses"].items():
            expense_data.append({
                "Category": category,
                "Budget": f"KD {values['budget']:.2f}",
                "Actual": f"KD {values['actual']:.2f}",
                "Variance": f"KD {values['actual'] - values['budget']:.2f}",
                "% of Budget": f"{(values['actual'] / values['budget'] * 100):.1f}%" if values['budget'] > 0 else "N/A"
            })
        
        if expense_data:
            expense_df = pd.DataFrame(expense_data)
            st.dataframe(expense_df, use_container_width=True)
    
    # Close the mobile-stack div
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Budget visualization as text
    st.subheader("Budget Visualization")
    
    # Use a container to make this section responsive
    with st.container():
        st.write(f"Income Budget: KD {total_income_budget:.2f}, Actual: KD {total_income_actual:.2f}")
        st.write(f"Expense Budget: KD {total_expense_budget:.2f}, Actual: KD {total_expense_actual:.2f}")
        st.write(f"Net Budget: KD {total_income_budget - total_expense_budget:.2f}, Actual: KD {total_income_actual - total_expense_actual:.2f}")

# Events function
def show_events():
    st.header("Event Management")
    
    # Add new event
    with st.expander("Create New Event Budget", expanded=True):
        # Add the responsive-form class
        st.markdown('<div class="responsive-form">', unsafe_allow_html=True)
        
        with st.form("event_form"):
            # Use the mobile-stack class for responsive columns
            cols_div = '<div class="mobile-stack">'
            st.markdown(cols_div, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                event_name = st.text_input("Event Name")
                event_date = st.date_input("Date")
                location = st.text_input("Location")
            
            with col2:
                coordinator = st.selectbox("Event Coordinator", list(committee_members.keys()))
                projected_income = st.number_input("Projected Income (KD)", min_value=0.0, format="%.2f")
                projected_expenses = st.number_input("Projected Expenses (KD)", min_value=0.0, format="%.2f")
            
            # Close the mobile-stack div
            st.markdown('</div>', unsafe_allow_html=True)
            
            submit = st.form_submit_button("Create Event Budget", use_container_width=True)
            
            if submit:
                if not event_name or not event_date:
                    st.error("Event name and date are required")
                else:
                    success, message = create_event_budget(
                        event_name,
                        event_date.strftime("%Y-%m-%d"),
                        location,
                        coordinator,
                        projected_income,
                        projected_expenses
                    )
                    
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
        
        # Close the responsive-form div
        st.markdown('</div>', unsafe_allow_html=True)
    
    # View events
    st.subheader("Planned Events")
    
    if st.session_state.events:
        try:
            events_df = pd.DataFrame(st.session_state.events)
            # Format currency columns
            events_df["projected_income"] = events_df["projected_income"].apply(lambda x: f"KD {x:.2f}")
            events_df["projected_expenses"] = events_df["projected_expenses"].apply(lambda x: f"KD {x:.2f}")
            events_df["actual_income"] = events_df["actual_income"].apply(lambda x: f"KD {x:.2f}")
            events_df["actual_expenses"] = events_df["actual_expenses"].apply(lambda x: f"KD {x:.2f}")
            # Rename columns for display
            display_df = events_df.rename(columns={
                "name": "Event Name",
                "date": "Date",
                "location": "Location",
                "coordinator": "Coordinator",
                "projected_income": "Projected Income",
                "projected_expenses": "Projected Expenses",
                "actual_income": "Actual Income",
                "actual_expenses": "Actual Expenses",
                "status": "Status"
            })
            # Select columns to display
            display_columns = [col for col in ["Event Name", "Date", "Location", "Coordinator", 
                               "Projected Income", "Projected Expenses", "Status"]
                               if col in display_df.columns]
            st.dataframe(display_df[display_columns], use_container_width=True)
        except Exception as e:
            st.error(f"Error displaying events: {e}")
            st.write(events_df)
        
        # Event details
        st.subheader("Event Details")
        selected_event = st.selectbox("Select event to view details", 
                                     [e["name"] for e in st.session_state.events])
        
        if selected_event:
            event = next((e for e in st.session_state.events if e["name"] == selected_event), None)
            
            if event:
                # Use the mobile-stack class for responsive columns
                cols_div = '<div class="mobile-stack">'
                st.markdown(cols_div, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader(event["name"])
                    st.write(f"**Date:** {event['date']}")
                    st.write(f"**Location:** {event['location']}")
                    st.write(f"**Coordinator:** {event['coordinator']}")
                    st.write(f"**Status:** {event['status']}")
                
                with col2:
                    # Financial summary
                    st.subheader("Financial Summary")
                    projected_profit = event["projected_income"] - event["projected_expenses"]
                    actual_profit = event["actual_income"] - event["actual_expenses"]
                    
                    st.write(f"**Projected Income:** KD {event['projected_income']:.2f}")
                    st.write(f"**Projected Expenses:** KD {event['projected_expenses']:.2f}")
                    st.write(f"**Projected Profit:** KD {projected_profit:.2f}")
                    st.write(f"**Actual Income:** KD {event['actual_income']:.2f}")
                    st.write(f"**Actual Expenses:** KD {event['actual_expenses']:.2f}")
                    st.write(f"**Actual Profit:** KD {actual_profit:.2f}")
                
                # Close the mobile-stack div
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Update event status
                new_status = st.selectbox("Update Status", 
                                         ["Planning", "Active", "Completed"],
                                         index=["Planning", "Active", "Completed"].index(event["status"]))
                
                if new_status != event["status"]:
                    event["status"] = new_status
                    st.success(f"Updated {event['name']} status to {new_status}")
                
                # Update actual figures
                with st.expander("Update Actual Figures"):
                    # Add the responsive-form class
                    st.markdown('<div class="responsive-form">', unsafe_allow_html=True)
                    
                    # Use the mobile-stack class for responsive columns
                    cols_div = '<div class="mobile-stack">'
                    st.markdown(cols_div, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        new_income = st.number_input("Actual Income (KD)", 
                                                   min_value=0.0, 
                                                   value=float(event["actual_income"]),
                                                   format="%.2f")
                    
                    with col2:
                        new_expenses = st.number_input("Actual Expenses (KD)", 
                                                     min_value=0.0, 
                                                     value=float(event["actual_expenses"]),
                                                     format="%.2f")
                    
                    # Close the mobile-stack div
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    if st.button("Update Figures", use_container_width=True):
                        event["actual_income"] = new_income
                        event["actual_expenses"] = new_expenses
                        st.success("Updated actual figures")
                    
                    # Close the responsive-form div
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No events created yet.")

# Reports function (simplified version)
def show_reports():
    st.header("Financial Reports")
    
    # Report type selection - use a container for responsiveness
    with st.container():
        report_type = st.radio("Report Type", 
                              ["Monthly Summary", "Year-to-Date", "Event Analysis", "Fundraising Results"],
                              horizontal=True if st.session_state.device_type != "mobile" else False)
    
    if report_type == "Monthly Summary":
        # Month and year selection
        # Use the mobile-stack class for responsive columns
        cols_div = '<div class="mobile-stack">'
        st.markdown(cols_div, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            month_names = [
                "January", "February", "March", "April", "May", "June", 
                "July", "August", "September", "October", "November", "December"
            ]
            selected_month = st.selectbox("Month", month_names)
            month_index = month_names.index(selected_month) + 1
        
        with col2:
            current_year = datetime.datetime.now().year
            selected_year = st.selectbox("Year", 
                                        list(range(current_year-2, current_year+3)))
        
        # Close the mobile-stack div
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Generate report
        if st.button("Generate Report", use_container_width=True):
            report = generate_monthly_report(month_index, selected_year)
            
            # Display report
            st.subheader(f"Monthly Financial Report - {selected_month} {selected_year}")
            
            # Summary metrics
            # Use the mobile-stack class for responsive columns
            cols_div = '<div class="mobile-stack">'
            st.markdown(cols_div, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Income", f"KD {report['total_income']:.2f}")
            
            with col2:
                st.metric("Total Expenses", f"KD {report['total_expenses']:.2f}")
            
            with col3:
                st.metric("Net", f"KD {report['net']:.2f}")
            
            # Close the mobile-stack div
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Overall financial position
            st.subheader("Overall Financial Position")
            
            # Use the mobile-stack class for responsive columns
            cols_div = '<div class="mobile-stack">'
            st.markdown(cols_div, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Current Balance", f"KD {report['current_balance']:.2f}")
            
            with col2:
                st.metric("Emergency Reserve", f"KD {report['emergency_reserve']:.2f}")
            
            with col3:
                st.metric("Available Funds", f"KD {report['available_funds']:.2f}")
            
            # Close the mobile-stack div
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Transactions
            st.subheader("Transactions")
            
            if report['transactions']:
                transactions_df = pd.DataFrame(report['transactions'])
                # Format currency columns
                transactions_df["income"] = transactions_df["income"].apply(lambda x: f"KD {x:.2f}" if x > 0 else "")
                transactions_df["expense"] = transactions_df["expense"].apply(lambda x: f"KD {x:.2f}" if x > 0 else "")
                # Select columns to display
                display_columns = [col for col in ["date", "description", "category", "income", "expense", "authorized_by"]
                                  if col in transactions_df.columns]
                st.dataframe(transactions_df[display_columns], use_container_width=True)
            else:
                st.info("No transactions for this period.")
    
    else:
        st.info(f"{report_type} reports are available in the full version.")
        st.write("Please add transactions and events to generate more detailed reports.")

# Fundraising function (simplified)
def show_fundraising():
    st.header("Fundraising Management")
    
    # Add new fundraising initiative
    with st.expander("Add New Fundraising Initiative", expanded=True):
        # Add the responsive-form class
        st.markdown('<div class="responsive-form">', unsafe_allow_html=True)
        
        with st.form("fundraising_form"):
            # Use the mobile-stack class for responsive columns
            cols_div = '<div class="mobile-stack">'
            st.markdown(cols_div, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Initiative Name")
                dates = st.text_input("Dates (e.g., Apr 15-20)")
            
            with col2:
                coordinator = st.selectbox("Coordinator", list(committee_members.keys()))
                goal_amount = st.number_input("Goal Amount (KD)", min_value=0.0, format="%.2f")
            
            # Close the mobile-stack div
            st.markdown('</div>', unsafe_allow_html=True)
            
            submit = st.form_submit_button("Add Initiative", use_container_width=True)
            
            if submit:
                if not name:
                    st.error("Initiative name is required")
                else:
                    success, message = add_fundraising_initiative(
                        name,
                        dates,
                        coordinator,
                        goal_amount
                    )
                    
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
        
        # Close the responsive-form div
        st.markdown('</div>', unsafe_allow_html=True)
    
    # View fundraising initiatives
    st.subheader("Fundraising Initiatives")
    
    if st.session_state.fundraising:
        try:
            fundraising_df = pd.DataFrame(st.session_state.fundraising)
            # Format currency columns
            fundraising_df["goal_amount"] = fundraising_df["goal_amount"].apply(lambda x: f"KD {x:.2f}")
            fundraising_df["actual_raised"] = fundraising_df["actual_raised"].apply(lambda x: f"KD {x:.2f}")
            fundraising_df["expenses"] = fundraising_df["expenses"].apply(lambda x: f"KD {x:.2f}")
            fundraising_df["net_proceeds"] = fundraising_df["net_proceeds"].apply(lambda x: f"KD {x:.2f}")
            # Rename columns for display
            display_df = fundraising_df.rename(columns={
                "name": "Initiative Name",
                "dates": "Dates",
                "coordinator": "Coordinator",
                "goal_amount": "Goal Amount",
                "actual_raised": "Amount Raised",
                "expenses": "Expenses",
                "net_proceeds": "Net Proceeds",
                "status": "Status"
            })
            # Select columns to display
            display_columns = [col for col in ["Initiative Name", "Dates", "Coordinator", 
                              "Goal Amount", "Amount Raised", "Status"]
                              if col in display_df.columns]
            st.dataframe(display_df[display_columns], use_container_width=True)
        except Exception as e:
            st.error(f"Error displaying fundraising initiatives: {e}")
            st.write(fundraising_df)
    else:
        st.info("No fundraising initiatives created yet.")

# Save and load functions
def save_data():
    data = {
        "budget": st.session_state.budget,
        "transactions": st.session_state.transactions,
        "events": st.session_state.events,
        "fundraising": st.session_state.fundraising
    }
    
    # Convert to JSON
    json_data = json.dumps(data, indent=4)
    
    # Provide download link
    st.download_button(
        label="Download Data Backup",
        data=json_data,
        file_name="financial_system_backup.json",
        mime="application/json",
        use_container_width=True
    )
    
    st.success("Data prepared for download")

def load_data():
    uploaded_file = st.file_uploader("Upload backup file", type=["json"])
    
    if uploaded_file:
        try:
            # Read the file
            data = json.load(uploaded_file)
            
            # Update session state
            st.session_state.budget = data.get("budget", st.session_state.budget)
            st.session_state.transactions = data.get("transactions", st.session_state.transactions)
            st.session_state.events = data.get("events", st.session_state.events)
            st.session_state.fundraising = data.get("fundraising", st.session_state.fundraising)
            
            st.success("Data loaded successfully")
            st.rerun()
        except Exception as e:
            st.error(f"Error loading data: {e}")

# Logout function
def logout():
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.username = None
    st.rerun()

# Settings functions
def show_settings():
    st.header("Settings")
    
    # Save/Load data
    st.subheader("Data Backup and Restore")
    
    # Use the mobile-stack class for responsive columns
    cols_div = '<div class="mobile-stack">'
    st.markdown(cols_div, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("Save current data to a file:")
        if st.button("Prepare Backup File", use_container_width=True):
            save_data()
    
    with col2:
        st.write("Load data from a backup file:")
        load_data()
    
    # Close the mobile-stack div
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Password management
    st.subheader("User Management")
    st.info("For security reasons, user credentials can only be modified directly in the source code.")
    st.write("Please contact the system administrator to add or update user accounts.")
    
    # Display current user info
    st.subheader("Current Login Information")
    st.write(f"**Username:** {st.session_state.username}")
    st.write(f"**Role:** {st.session_state.user_role}")
    st.write(f"**Login time:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Main app
def main():
    # Check if user is authenticated
    if not st.session_state.authenticated:
        show_login()
        return
    
    # Sidebar navigation
    st.sidebar.title("Year 11 Committee")
    st.sidebar.subheader("Financial Management System")
    
    # Display user role
    st.sidebar.info(f"Logged in as: {st.session_state.username.upper()} ({st.session_state.user_role})")
    
    # Add logout button
    if st.sidebar.button("Logout", use_container_width=True):
        logout()
    
    # Set default page if not exists
    if 'page' not in st.session_state:
        st.session_state.page = 'dashboard'
    
    # Navigate based on user role
    if st.session_state.user_role == "admin":
        # Full access for admin
        page = st.sidebar.radio("Navigation", 
                               ["Dashboard", "Transactions", "Budget", "Events", 
                                "Fundraising", "Reports", "Settings"],
                               index=["dashboard", "transactions", "budget", "events", 
                                     "fundraising", "reports", "settings"].index(st.session_state.page))
    else:
        # Limited access for viewer
        page = st.sidebar.radio("Navigation", 
                               ["Dashboard", "Reports"],
                               index=["dashboard", "reports"].index(st.session_state.page)
                               if st.session_state.page in ["dashboard", "reports"] else 0)
    
    # Store the current page
    st.session_state.page = page.lower()
    
    # Display the selected page based on user role
    if st.session_state.page == 'dashboard':
        show_dashboard()
    elif st.session_state.page == 'reports':
        show_reports()
    elif st.session_state.user_role == "admin":
        # Only admin can access these pages
        if st.session_state.page == 'transactions':
            show_transactions()
        elif st.session_state.page == 'budget':
            show_budget()
        elif st.session_state.page == 'events':
            show_events()
        elif st.session_state.page == 'fundraising':
            show_fundraising()
        elif st.session_state.page == 'settings':
            show_settings()
    
    # Display footer
    st.sidebar.markdown("---")
    st.sidebar.info(
        "Developed by Deema Abououf\n\n"
        "Treasurer/Finance Manager\n"
        "Year 11 Committee"
    )

if __name__ == '__main__':
    main()