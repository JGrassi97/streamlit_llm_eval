import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from hashlib import sha256

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
        return False
    user_ws.append_row([
        email,
        hash_password(password),
        background,
        role,
        "yes" if wants_updates else "no"
    ])
    return True


def login_user(email, password):
    users = pd.DataFrame(user_ws.get_all_records())
    row = users[users.email == email]
    if row.empty:
        return None
    if row.iloc[0]["password"] == hash_password(password):
        return email
    return None

# === UI ===
st.title("Account Management")

menu = ["Login", "Register", "Logout"]
choice = st.selectbox("Action", menu)

if "user_email" not in st.session_state:
    st.session_state.user_email = None

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
        if register_user(email, password, background, role, wants_updates):
            st.success("Registration successful. You can now log in.")
        else:
            st.error("Email already registered.")

elif choice == "Login":
    st.subheader("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user_email = login_user(email, password)
        if user_email:
            st.session_state.user_email = user_email
            st.success(f"Logged in as: {user_email}")
        else:
            st.error("Invalid credentials.")

elif choice == "Logout":
    st.session_state.user_email = None
    st.success("Logged out successfully.")

# === Visualizza valutazioni dell'utente ===
if st.session_state.user_email:
    st.subheader("📊 Your past evaluations")

    @st.cache_data(ttl=60)
    def load_user_evaluations(email):
        df = pd.DataFrame(eval_ws.get_all_records())
        return df[df["email"] == email] if not df.empty else pd.DataFrame()

    user_evals = load_user_evaluations(st.session_state.user_email)

    st.subheader("📁 Review individual responses")

    # Trova le question_id uniche valutate
    question_ids = user_evals["question_id"].unique().tolist()
    question_ids.sort()

    selected_qid = st.selectbox("Select a question to review", question_ids)

    # Filtra righe associate a quella domanda
    q_rows = user_evals[user_evals["question_id"] == selected_qid]

    if len(q_rows) == 2:
        agent_A, agent_B = q_rows["agent"].tolist()
        score_A = q_rows[q_rows["agent"] == agent_A].iloc[0]
        score_B = q_rows[q_rows["agent"] == agent_B].iloc[0]

        idx = selected_qid.replace("Q", "")

        def load_response(agent, idx):
            import os, json
            path = os.path.join("responses/gpt-4.1", agent, f"response_{idx}.json")
            with open(path) as f:
                return json.load(f)

        resp_A = load_response(agent_A, idx)
        resp_B = load_response(agent_B, idx)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"### {agent_A}")
            st.markdown(resp_A["ResponseText"])
            st.markdown("**Scores**")
            st.write({
                "Relevance": score_A["relevance"],
                "Credibility": score_A["credibility"],
                "Uncertainty": score_A["uncertainty"],
                "Actionability": score_A["actionability"]
            })

        with col2:
            st.markdown(f"### {agent_B}")
            st.markdown(resp_B["ResponseText"])
            st.markdown("**Scores**")
            st.write({
                "Relevance": score_B["relevance"],
                "Credibility": score_B["credibility"],
                "Uncertainty": score_B["uncertainty"],
                "Actionability": score_B["actionability"]
            })

        st.warning("If you delete, both responses for this question will be removed.")

        if st.button("🗑️ Delete this evaluation"):
            # Rimuovi entrambe le righe
            all_records = eval_ws.get_all_values()
            header = all_records[0]
            rows = all_records[1:]

            to_keep = [
                row for row in rows
                if not (row[0] == st.session_state.user_email and row[1] == selected_qid)
            ]

            eval_ws.clear()
            eval_ws.append_row(header)
            for r in to_keep:
                eval_ws.append_row(r)

            st.success("Evaluation deleted. Reloading...")
            st.rerun()

    else:
        st.info("Incomplete evaluation for this question.")

