import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

import json
import os
import random
import re

RESPONSE_BASE_PATH = "responses/gpt-4.1"

# Set wide layout
st.set_page_config(layout="wide", page_title="AI for Climate Adaptation – Evaluation")


def split_sections(response_text):
    # Estrae blocchi principali (naive, da migliorare se serve)
    sections = {}
    current = None
    for line in response_text.split("\n"):
        line = line.strip()

        # Salta linee che creano linee orizzontali
        if line in ("---", "***", "___"):
            continue

        if line.lower().startswith("### executive summary"):
            current = "Executive summary"
            sections[current] = ""
        elif line.lower().startswith("### uncertainty"):
            current = "Uncertainty"
            sections[current] = ""
        elif line.lower().startswith("### actionability"):
            current = "Actionability"
            sections[current] = ""
        elif line.lower().startswith("### credibility"):
            current = "Credibility"
            sections[current] = ""
        elif current:
            sections[current] += line + "\n"
    return sections

# === Caricamento risposte ===
def load_response(agent_name, idx):
    path = os.path.join(RESPONSE_BASE_PATH, agent_name, f"response_{idx}.json")
    with open(path, "r") as f:
        return json.load(f)

def get_random_evaluation_pair(already_done):
    indices = [f.split("_")[1].split(".")[0] for f in os.listdir(os.path.join(RESPONSE_BASE_PATH, "Plain-LLM"))]
    random.shuffle(indices)
    others = ["Climsight", "Climsight-XCLIM", "XCLIM-AI"]

    for idx in indices:
        plain = load_response("Plain-LLM", idx)
        alt_agent = random.choice(others)
        alt = load_response(alt_agent, idx)

        pair = [("Q" + idx, "Plain-LLM"), ("Q" + idx, alt["Agent"])]
        if not any(p in already_done for p in pair):
            return idx, plain, alt

    return None, None, None  # Nessuna nuova combinazione trovata

# === Setup Google Sheet ===
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(st.secrets["gspread"], scopes=scope)
gc = gspread.authorize(credentials)
sh = gc.open_by_url(st.secrets["gspread"]["sheet_url"])
eval_ws = sh.worksheet("evaluations")

def save_evaluation(user_id, question_id, agent, relevance, credibility, usability, actionability):
    eval_ws.append_row([user_id, question_id, agent, relevance, credibility, usability, actionability])

# === UI iniziale ===
st.title("Evaluation")

if "user_email" not in st.session_state or not st.session_state.user_email:
    st.warning("Please log in first on the 'Account Management' page.")
    st.stop()

st.success(f"You are logged in as: {st.session_state.user_email} (ID: {st.session_state.user_id})")

# === Carica valutazioni precedenti dell'utente ===
@st.cache_data(ttl=60)
def load_user_evaluations(user_id):
    df = pd.DataFrame(eval_ws.get_all_records())
    return df[df["user_id"] == user_id] if not df.empty else pd.DataFrame()

user_eval_df = load_user_evaluations(st.session_state.user_id)
already_done = set(tuple(x) for x in user_eval_df[["question_id", "agent"]].dropna().values.tolist())

# === Mostra sempre il bottone per rigenerare
col_refresh, _ = st.columns([1, 5])
with col_refresh:
    if st.button("🔄 Change question"):
        st.session_state.force_refresh = True

# === Genera nuova domanda se serve
if "eval_idx" not in st.session_state or st.session_state.get("force_refresh", False):
    idx, plain, other = get_random_evaluation_pair(already_done)
    if idx is None:
        st.info("You have completed all available evaluations 🎉")
        st.stop()

    responses = [
        {"label": "Response A", "content": plain["ResponseText"], "agent": "Plain-LLM"},
        {"label": "Response B", "content": other["ResponseText"], "agent": other["Agent"]}
    ]
    random.shuffle(responses)

    st.session_state.eval_idx = idx
    st.session_state.responses = responses
    st.session_state.force_refresh = False  # reset flag


# === Mostra domanda e risposte ===
idx = st.session_state.eval_idx
responses = st.session_state.responses
response_id = f"Q{idx}"
question_text = load_response("Plain-LLM", idx)["QuestionText"]

st.markdown(f"### Question {response_id}")
st.markdown(f"**{question_text}**")
st.markdown("---")

# Ottieni le sezioni per entrambe le risposte
sections_A = split_sections(responses[0]["content"])
sections_B = split_sections(responses[1]["content"])

options = {
    1: "Not at all",
    2: "Slightly", 
    3: "Moderately",
    4: "Very",
    5: "Extremely"
}

# === RELEVANCE SECTION ===
st.header("📊 Relevance")
st.markdown("*How well does each response address the given question?*")

col1, col2, col3 = st.columns([8, 1, 8])

with col1:
    st.markdown("#### Response A")
    with st.container(border=True):
        st.markdown("##### Executive Summary")
        st.markdown(sections_A.get("Executive summary", "*No summary found.*"))

with col3:
    st.markdown("#### Response B") 
    with st.container(border=True):
        st.markdown("##### Executive Summary")
        st.markdown(sections_B.get("Executive summary", "*No summary found.*"))

# Valutazioni Relevance
st.markdown("##### Rate the relevance of each response:")
col1, col2, col3 = st.columns([8, 1, 8])

with col1:
    rel_A = st.radio("Response A - Relevance", options, format_func=options.get, key="rel_A", horizontal=True)

with col3:
    rel_B = st.radio("Response B - Relevance", options, format_func=options.get, key="rel_B", horizontal=True)

st.markdown("---")

# === CREDIBILITY SECTION ===
st.header("🔬 Credibility")
st.markdown("*Scientific accuracy and plausibility of the information*")

col1, col2, col3 = st.columns([8, 1, 8])

with col1:
    st.markdown("#### Response A")
    with st.container(border=True):
        st.markdown("##### Credibility")
        st.markdown(sections_A.get("Credibility", "*No credibility section found.*"))

with col3:
    st.markdown("#### Response B")
    with st.container(border=True):
        st.markdown("##### Credibility")  
        st.markdown(sections_B.get("Credibility", "*No credibility section found.*"))

# Valutazioni Credibility
st.markdown("##### Rate the credibility of each response:")
col1, col2, col3 = st.columns([8, 1, 8])

with col1:
    cred_A = st.radio("Response A - Credibility", options, format_func=options.get, key="cred_A", horizontal=True)

with col3:
    cred_B = st.radio("Response B - Credibility", options, format_func=options.get, key="cred_B", horizontal=True)

st.markdown("---")

# === UNCERTAINTY SECTION ===
st.header("❓ Uncertainty Communication")
st.markdown("*Clarity in expressing limitations or confidence levels*")

col1, col2, col3 = st.columns([8, 1, 8])

with col1:
    st.markdown("#### Response A")
    with st.container(border=True):
        st.markdown("##### Uncertainty")
        st.markdown(sections_A.get("Uncertainty", "*No uncertainty section found.*"))

with col3:
    st.markdown("#### Response B")
    with st.container(border=True):
        st.markdown("##### Uncertainty")
        st.markdown(sections_B.get("Uncertainty", "*No uncertainty section found.*"))

# Valutazioni Uncertainty
st.markdown("##### Rate the uncertainty communication of each response:")
col1, col2, col3 = st.columns([8, 1, 8])

with col1:
    uncer_A = st.radio("Response A - Uncertainty", options, format_func=options.get, key="uncer_A", horizontal=True)

with col3:
    uncer_B = st.radio("Response B - Uncertainty", options, format_func=options.get, key="uncer_B", horizontal=True)

st.markdown("---")

# === ACTIONABILITY SECTION ===
st.header("🎯 Actionability")
st.markdown("*Usefulness of the response for decision-making or planning*")

col1, col2, col3 = st.columns([8, 1, 8])

with col1:
    st.markdown("#### Response A")
    with st.container(border=True):
        st.markdown("##### Actionability")
        st.markdown(sections_A.get("Actionability", "*No actionability section found.*"))

with col3:
    st.markdown("#### Response B")
    with st.container(border=True):
        st.markdown("##### Actionability")
        st.markdown(sections_B.get("Actionability", "*No actionability section found.*"))

# Valutazioni Actionability
st.markdown("##### Rate the actionability of each response:")
col1, col2, col3 = st.columns([8, 1, 8])

with col1:
    action_A = st.radio("Response A - Actionability", options, format_func=options.get, key="action_A", horizontal=True)

with col3:
    action_B = st.radio("Response B - Actionability", options, format_func=options.get, key="action_B", horizontal=True)

st.markdown("---")

# === Submit Evaluation ===
st.header("📝 Submit Your Evaluation")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("✅ Send Evaluation", type="primary", use_container_width=True):
        save_evaluation(st.session_state.user_id, response_id, responses[0]['agent'], rel_A, cred_A, uncer_A, action_A)
        save_evaluation(st.session_state.user_id, response_id, responses[1]['agent'], rel_B, cred_B, uncer_B, action_B)
        st.success(f"✅ Evaluations for question {response_id} saved!")

        for k in [
            "rel_A", "cred_A", "uncer_A", "action_A",
            "rel_B", "cred_B", "uncer_B", "action_B",
            "eval_idx", "responses"
        ]:
            st.session_state.pop(k, None)

        st.rerun()
