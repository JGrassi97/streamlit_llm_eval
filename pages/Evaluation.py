import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import uuid

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
user_ws = sh.worksheet("users")

# === Funzioni di gestione utenti ===
def check_user_exists(username):
    """Controlla se l'username esiste già nel Google Sheet"""
    users = pd.DataFrame(user_ws.get_all_records())
    if users.empty:
        return False, None
    user_row = users[users["username"] == username]
    if user_row.empty:
        return False, None
    return True, user_row.iloc[0]["user_id"]

def create_new_user(username, background, role, institution, climate_experience=None, education_level=None, geographic_region=None, ai_familiarity=None, motivation=None):
    """Crea un nuovo utente nel Google Sheet"""
    user_id = str(uuid.uuid4())[:8]  # Usa solo i primi 8 caratteri per semplicità
    
    # Se non vengono forniti i nuovi parametri, usa valori di default per compatibilità
    if climate_experience is None:
        climate_experience = "Not specified"
    if education_level is None:
        education_level = "Not specified"
    if geographic_region is None:
        geographic_region = "Not specified"
    if ai_familiarity is None:
        ai_familiarity = "Not specified"
    if motivation is None:
        motivation = "Not specified"
    
    user_ws.append_row([
        user_id,
        username,
        background,
        role,
        institution,
        climate_experience,
        education_level,
        geographic_region,
        ai_familiarity,
        motivation
    ])
    return user_id

def save_evaluation(user_id, question_id, agent, relevance, credibility, uncertainty, actionability):
    eval_ws.append_row([user_id, question_id, agent, relevance, credibility, uncertainty, actionability])

# === UI iniziale ===
st.title("Evaluation")

# Inizializza le variabili di sessione
if "user_username" not in st.session_state:
    st.session_state.user_username = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "show_registration_form" not in st.session_state:
    st.session_state.show_registration_form = False

# === Sistema di autenticazione semplificato ===
if not st.session_state.user_username:
    
    # Form di registrazione per nuovo utente
    if st.session_state.show_registration_form:
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("### ✨ Welcome!")
            st.markdown(f"Great choice with username **{st.session_state.new_username}**!")
            
            # Banner informativo
            st.info(
                "📝 **Help us understand our evaluators better**\n\n"
                "These questions help us analyze the diversity of perspectives in our research. "
                "**All fields are optional** - you can skip any question you prefer not to answer."
            )
            
            with st.form("registration_form"):
                st.markdown("#### About You")
                
                background = st.text_area(
                    "Professional background or field of interest",
                    help="e.g., Environmental science, Policy analysis, Climate research, Engineering...",
                    placeholder="Optional - Tell us about your professional background or areas of interest"
                )
                
                role = st.selectbox(
                    "Current role", 
                    ["Prefer not to say", "Student", "Researcher", "Policymaker", "NGO", "Private Sector", "Consultant", "Journalist", "Other"],
                    help="Optional - Select your current professional role"
                )
                
                institution = st.text_input(
                    "Institution/Organization",
                    help="e.g., University, Company, Government Agency, NGO...",
                    placeholder="Optional - Your current institution or organization"
                )
                
                # Nuove domande per profilazione
                st.markdown("#### Experience & Expertise")
                
                climate_experience = st.selectbox(
                    "Experience with climate change topics",
                    ["Prefer not to say", "No specific experience", "Basic knowledge", "Some experience", "Experienced", "Expert level"],
                    help="Optional - Your level of experience with climate change and adaptation topics"
                )
                
                education_level = st.selectbox(
                    "Highest education level",
                    ["Prefer not to say", "High school", "Bachelor's degree", "Master's degree", "PhD", "Other"],
                    help="Optional - Your highest completed education level"
                )
                
                geographic_region = st.selectbox(
                    "Geographic region",
                    ["Prefer not to say", "Europe", "North America", "South America", "Asia", "Africa", "Oceania", "Other"],
                    help="Optional - The region where you are based"
                )
                
                ai_familiarity = st.selectbox(
                    "Familiarity with AI/LLMs",
                    ["Prefer not to say", "Not familiar", "Basic understanding", "Regular user", "Professional user", "AI researcher/developer"],
                    help="Optional - Your level of familiarity with AI and Large Language Models"
                )
                
                motivation = st.text_area(
                    "What interests you about this evaluation?",
                    help="Optional - What motivated you to participate in this research?",
                    placeholder="Optional - e.g., Interest in climate science, AI research, contributing to research..."
                )
                
                st.markdown("")
                submitted = st.form_submit_button("Continue", use_container_width=True)
                
                if submitted:
                    # Crea nuovo utente (tutti i campi sono opzionali tranne username)
                    user_id = create_new_user(
                        st.session_state.new_username,
                        background.strip() if background.strip() else "Not specified",
                        role if role != "Prefer not to say" else "Not specified",
                        institution.strip() if institution.strip() else "Not specified",
                        climate_experience if climate_experience != "Prefer not to say" else "Not specified",
                        education_level if education_level != "Prefer not to say" else "Not specified", 
                        geographic_region if geographic_region != "Prefer not to say" else "Not specified",
                        ai_familiarity if ai_familiarity != "Prefer not to say" else "Not specified",
                        motivation.strip() if motivation.strip() else "Not specified"
                    )
                    
                    # Imposta sessione
                    st.session_state.user_username = st.session_state.new_username
                    st.session_state.user_id = user_id
                    st.session_state.show_registration_form = False
                    
                    st.success(f"Welcome aboard, {st.session_state.new_username}! 🎉")
                    st.success(f"Your evaluator ID is: **{user_id}**")
                    st.info("Starting your evaluation session...")
                    st.rerun()
            
            st.markdown("")  # Spazio
            if st.button("← Back to username", key="cancel_registration", use_container_width=True):
                st.session_state.show_registration_form = False
                st.session_state.new_username = None
                st.rerun()
    
    else:
        # Sezione di login (solo se NON siamo nel form di registrazione)
        # Centrare il form di login
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("### Enter your username")
            st.markdown("")
            
            username = st.text_input(
                "Username", 
                key="login_username",
                placeholder="Choose a unique username...",
                help="This will be your identifier for this evaluation session"
            )
            
            st.markdown("**New to the platform?** Choose any username you like and write it down somewhere safe - you'll need it to access your evaluations later.")
            st.markdown("**Returning user?** Enter the same username you used before.")
            
            st.markdown("")
            
            if st.button("Continue", key="login_button", use_container_width=True):
                if username.strip():
                    # Controlla se l'utente esiste
                    user_exists, user_id = check_user_exists(username.strip())
                    
                    if user_exists:
                        # Utente esistente, procedi alla valutazione
                        st.session_state.user_username = username.strip()
                        st.session_state.user_id = user_id
                        st.session_state.show_registration_form = False
                        st.success(f"Welcome back, {username}!")
                        st.rerun()
                    else:
                        # Nuovo utente, mostra form di registrazione
                        st.session_state.show_registration_form = True
                        st.session_state.new_username = username.strip()
                        st.rerun()
                else:
                    st.error("Please enter a valid username.")
            
            st.markdown("---")
            
        # Info box centrato
        st.info(
            "ℹ️ **Why do we need a username?**\n\n"
            "We need to track how many people participate in the evaluation and which responses each person evaluates "
            "to ensure the quality and validity of our research. However, **your individual responses remain completely anonymous** "
            "and will only be used for scientific research purposes."
        )
    
    st.stop()

# === Utente autenticato ===
st.success(f"You are logged in as: {st.session_state.user_username} (ID: {st.session_state.user_id})")

# Bottone di logout
col1, col2 = st.columns([1, 5])
with col1:
    if st.button("🚪 Logout"):
        st.session_state.user_username = None
        st.session_state.user_id = None
        st.session_state.show_registration_form = False
        st.rerun()

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
