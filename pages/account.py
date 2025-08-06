import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from hashlib import sha256
import uuid

# === Setup Google Sheets ===
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(st.secrets["gspread"], scopes=scope)
gc = gspread.authorize(credentials)
sh = gc.open_by_url(st.secrets["gspread"]["sheet_url"])
user_ws = sh.worksheet("users")
eval_ws = sh.worksheet("evaluations")  # nuovo

# === Funzioni di gestione utenti ===
def hash_password(password):
    return sha256(password.encode()).hexdigest()

def register_user(email, password, background, role, wants_updates):
    users = pd.DataFrame(user_ws.get_all_records())
    if email in users["email"].values:
        return False, None
    
    # Genera un ID univoco per il valutatore
    user_id = str(uuid.uuid4())[:8]  # Usa solo i primi 8 caratteri per semplicità
    
    user_ws.append_row([
        user_id,
        email,
        hash_password(password),
        background,
        role,
        "yes" if wants_updates else "no"
    ])
    return True, user_id


def login_user(email, password):
    users = pd.DataFrame(user_ws.get_all_records())
    row = users[users.email == email]
    if row.empty:
        return None, None
    if row.iloc[0]["password"] == hash_password(password):
        return email, row.iloc[0]["user_id"]
    return None, None

# === UI ===
st.title("Account Management")

menu = ["Login", "Register", "Logout"]
choice = st.selectbox("Action", menu)

if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None

if choice == "Register":
    st.subheader("Create a new account")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    background = st.text_area("Tell us a bit about your background (e.g. research field, interest)")
    role = st.selectbox("Your current role", ["Student", "Researcher", "Policymaker", "NGO", "Private Sector", "Other"])
    wants_updates = st.checkbox("I would like to receive email updates about this evaluation project")

    st.markdown(
        ":warning: **Important**: Your password will be encrypted but **we cannot guarantee full security**. "
        "Please **do not use a password that you use on other services**."
    )

    if st.button("Register"):
        success, user_id = register_user(email, password, background, role, wants_updates)
        if success:
            st.success(f"Registration successful! Your evaluator ID is: **{user_id}**")
            st.info("Please save your evaluator ID for reference. You can now log in.")
        else:
            st.error("Email already registered.")

elif choice == "Login":
    st.subheader("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user_email, user_id = login_user(email, password)
        if user_email:
            st.session_state.user_email = user_email
            st.session_state.user_id = user_id
            st.success(f"Logged in as: {user_email} (ID: {user_id})")
        else:
            st.error("Invalid credentials.")

elif choice == "Logout":
    st.session_state.user_email = None
    st.session_state.user_id = None
    st.success("Logged out successfully.")


