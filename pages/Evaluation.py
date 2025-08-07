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
@st.cache_data
def load_response(agent_name, idx):
    path = os.path.join(RESPONSE_BASE_PATH, agent_name, f"response_{idx}.json")
    with open(path, "r") as f:
        return json.load(f)

@st.cache_data
def get_available_indices():
    return [f.split("_")[1].split(".")[0] for f in os.listdir(os.path.join(RESPONSE_BASE_PATH, "Plain-LLM"))]

def get_random_evaluation_pair(already_done):
    indices = get_available_indices()
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

def save_evaluation(user_id, question_id, agent, relevance, credibility, uncertainty, actionability):
    eval_ws.append_row([user_id, question_id, agent, relevance, credibility, uncertainty, actionability])

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
        st.rerun()

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
    
    # Rimuovi le chiavi degli slider per resettarli alla prossima inizializzazione
    slider_keys = [
        "rel_A", "cred_A", "uncer_A", "action_A",
        "rel_B", "cred_B", "uncer_B", "action_B"
    ]
    for k in slider_keys:
        if k in st.session_state:
            del st.session_state[k]


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

# Inizializza gli slider se non esistono
slider_keys = [
    "rel_A", "cred_A", "uncer_A", "action_A",
    "rel_B", "cred_B", "uncer_B", "action_B"
]

for key in slider_keys:
    if key not in st.session_state:
        st.session_state[key] = 0

# Funzione per gestire gli slider in un fragment per ridurre il lag
@st.fragment
def render_relevance_sliders():
    st.markdown("##### Rate the relevance of each response:")
    col1, col2, col3 = st.columns([8, 1, 8])
    
    with col1:
        rel_A = st.slider("Response A - Relevance", 0, 10, key="rel_A", help="0 = Not selected, 1-10 = Rating scale")
    
    with col3:
        rel_B = st.slider("Response B - Relevance", 0, 10, key="rel_B", help="0 = Not selected, 1-10 = Rating scale")
    
    return rel_A, rel_B

@st.fragment
def render_credibility_sliders():
    st.markdown("##### Rate the credibility of each response:")
    col1, col2, col3 = st.columns([8, 1, 8])
    
    with col1:
        cred_A = st.slider("Response A - Credibility", 0, 10, key="cred_A", help="0 = Not selected, 1-10 = Rating scale")
    
    with col3:
        cred_B = st.slider("Response B - Credibility", 0, 10, key="cred_B", help="0 = Not selected, 1-10 = Rating scale")
    
    return cred_A, cred_B

@st.fragment
def render_uncertainty_sliders():
    st.markdown("##### Rate the uncertainty communication of each response:")
    col1, col2, col3 = st.columns([8, 1, 8])
    
    with col1:
        uncer_A = st.slider("Response A - Uncertainty", 0, 10, key="uncer_A", help="0 = Not selected, 1-10 = Rating scale")
    
    with col3:
        uncer_B = st.slider("Response B - Uncertainty", 0, 10, key="uncer_B", help="0 = Not selected, 1-10 = Rating scale")
    
    return uncer_A, uncer_B

@st.fragment
def render_actionability_sliders():
    st.markdown("##### Rate the actionability of each response:")
    col1, col2, col3 = st.columns([8, 1, 8])
    
    with col1:
        action_A = st.slider("Response A - Actionability", 0, 10, key="action_A", help="0 = Not selected, 1-10 = Rating scale")
    
    with col3:
        action_B = st.slider("Response B - Actionability", 0, 10, key="action_B", help="0 = Not selected, 1-10 = Rating scale")
    
    return action_A, action_B

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
rel_A, rel_B = render_relevance_sliders()

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
cred_A, cred_B = render_credibility_sliders()

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
uncer_A, uncer_B = render_uncertainty_sliders()

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
action_A, action_B = render_actionability_sliders()

st.markdown("---")

# === Submit Evaluation ===
st.header("📝 Submit Your Evaluation")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("✅ Send Evaluation", type="primary", use_container_width=True):
        # Verifica che tutti i valori siano diversi da 0
        if all([rel_A > 0, cred_A > 0, uncer_A > 0, action_A > 0, rel_B > 0, cred_B > 0, uncer_B > 0, action_B > 0]):
            save_evaluation(st.session_state.user_id, response_id, responses[0]['agent'], rel_A, cred_A, uncer_A, action_A)
            save_evaluation(st.session_state.user_id, response_id, responses[1]['agent'], rel_B, cred_B, uncer_B, action_B)
            st.success(f"✅ Evaluations for question {response_id} saved!")

            # Rimuovi le chiavi della sessione per generare nuova domanda e resettare slider
            for k in ["eval_idx", "responses"] + slider_keys:
                if k in st.session_state:
                    del st.session_state[k]

            st.rerun()
        else:
            st.error("⚠️ Please rate all criteria with values from 1 to 10 before submitting.")
