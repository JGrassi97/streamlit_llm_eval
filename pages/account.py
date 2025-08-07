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

def register_user(username, password, background, role, institution):
    users = pd.DataFrame(user_ws.get_all_records())
    if username in users["username"].values:
        return False, None
    
    # Genera un ID univoco per il valutatore
    user_id = str(uuid.uuid4())[:8]  # Usa solo i primi 8 caratteri per semplicità
    
    user_ws.append_row([
        user_id,
        username,
        hash_password(password),
        background,
        role,
        institution
    ])
    return True, user_id


def login_user(username, password):
    users = pd.DataFrame(user_ws.get_all_records())
    row = users[users.username == username]
    if row.empty:
        return None, None
    if row.iloc[0]["password"] == hash_password(password):
        return username, row.iloc[0]["user_id"]
    return None, None

# === UI ===
st.title("Account Management")

menu = ["Login", "Register", "Logout"]
choice = st.selectbox("Action", menu)

if "user_username" not in st.session_state:
    st.session_state.user_username = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None

if choice == "Register":
    st.subheader("Create a new account")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    background = st.text_area("Tell us a bit about your background (e.g. research field, interest)")
    role = st.selectbox("Your current role", ["Student", "Researcher", "Policymaker", "NGO", "Private Sector", "Other"])
    institution = st.text_input("Institution/Organization (e.g. University, Company, Government Agency)")

    st.markdown(
        ":warning: **Important**: Your password will be encrypted but **we cannot guarantee full security**. "
        "Please **do not use a password that you use on other services**."
    )

    if st.button("Register"):
        success, user_id = register_user(username, password, background, role, institution)
        if success:
            st.success(f"Registration successful! Your evaluator ID is: **{user_id}**")
            st.info("Please save your evaluator ID for reference. You can now log in.")
        else:
            st.error("Username already registered.")

elif choice == "Login":
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user_username, user_id = login_user(username, password)
        if user_username:
            st.session_state.user_username = user_username
            st.session_state.user_id = user_id
            st.success(f"Logged in as: {user_username} (ID: {user_id})")
        else:
            st.error("Invalid credentials.")

elif choice == "Logout":
    st.session_state.user_username = None
    st.session_state.user_id = None
    st.success("Logged out successfully.")


