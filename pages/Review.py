import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
import json
import os

# Set page config
st.set_page_config(layout="wide", page_title="Review - AI Climate Evaluation")

RESPONSE_BASE_PATH = "responses/gpt-4.1"

# === Authentication ===
def check_password():
    """Returns True if the user had the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Check if both username and password exist in session_state
        if ("username" in st.session_state and "password" in st.session_state and 
            st.session_state["username"] and st.session_state["password"]):
            
            if (st.session_state["username"] == st.secrets["stats_auth"]["username"] and 
                st.session_state["password"] == st.secrets["stats_auth"]["password"]):
                st.session_state["password_correct"] = True
                del st.session_state["password"]  # don't store password
                del st.session_state["username"]  # don't store username
            else:
                st.session_state["password_correct"] = False
        else:
            # If username or password is empty, mark as incorrect
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.title("🔐 Statistics Access")
        st.markdown("---")
        st.warning("The statistic page is not available to the public. Please authenticate to continue.")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("Username", key="username", on_change=password_entered)
            st.text_input("Password", type="password", key="password", on_change=password_entered)
            st.button("Login", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error
        st.title("🔐 Statistics Access") 
        st.markdown("---")
        st.error("Authentication failed. Please check your credentials.")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("Username", key="username", on_change=password_entered)
            st.text_input("Password", type="password", key="password", on_change=password_entered)
            st.button("Login", on_click=password_entered)
        return False
    else:
        # Password correct
        return True

# Check authentication before showing statistics
if not check_password():
    st.stop()


# === Setup Google Sheets ===
@st.cache_resource
def init_gsheets():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(st.secrets["gspread"], scopes=scope)
    gc = gspread.authorize(credentials)
    sh = gc.open_by_url(st.secrets["gspread"]["sheet_url"])
    return sh

@st.cache_data(ttl=300)  # Cache per 5 minuti
def load_evaluation_data():
    """Carica tutti i dati di valutazione dal Google Sheet"""
    sh = init_gsheets()
    eval_ws = sh.worksheet("evaluations")
    return pd.DataFrame(eval_ws.get_all_records())

@st.cache_data(ttl=300)
def load_user_data():
    """Carica i dati degli utenti dal Google Sheet"""
    sh = init_gsheets()
    user_ws = sh.worksheet("users")
    return pd.DataFrame(user_ws.get_all_records())

# === Caricamento risposte AI ===
@st.cache_data
def load_response(agent_name, idx):
    """Carica la risposta di un agente per una specifica domanda"""
    try:
        path = os.path.join(RESPONSE_BASE_PATH, agent_name, f"response_{idx}.json")
        with open(path, "r", encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

def split_sections(response_text):
    """Estrae le sezioni dalla risposta"""
    sections = {}
    current = None
    for line in response_text.split("\n"):
        line = line.strip()

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

# === Main UI ===
st.title("📋 Admin Review Dashboard")
st.success("✅ Admin authenticated successfully")

# Logout button
if st.button("🚪 Logout"):
    st.session_state["admin_password_correct"] = False
    st.rerun()

st.markdown("---")

# Carica i dati
try:
    eval_df = load_evaluation_data()
    user_df = load_user_data()
    
    if eval_df.empty:
        st.info("No evaluation data available yet.")
        st.stop()
    
    # Converte le colonne numeriche
    numeric_cols = ['relevance', 'credibility', 'uncertainty', 'actionability']
    for col in numeric_cols:
        if col in eval_df.columns:
            eval_df[col] = pd.to_numeric(eval_df[col], errors='coerce')
    
    # Merge con i dati utente per avere informazioni demografiche
    if not user_df.empty:
        eval_with_users = eval_df.merge(
            user_df[['user_id', 'role', 'institution']], 
            on='user_id', 
            how='left'
        )
    else:
        eval_with_users = eval_df.copy()
    
    # === Overview generale ===
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Questions", eval_df['question_id'].nunique())
    
    with col2:
        st.metric("Total Evaluations", len(eval_df))
    
    with col3:
        st.metric("Active Evaluators", eval_df['user_id'].nunique())
    
    with col4:
        st.metric("AI Agents", eval_df['agent'].nunique())
    
    st.markdown("---")
    
    # === Review per domanda ===
    st.header("📊 Detailed Review by Question")
    
    # Ottieni tutte le domande disponibili
    questions = sorted(eval_df['question_id'].unique())
    
    for question_id in questions:
        # Estrai il numero della domanda per caricare il testo
        q_num = question_id.replace('Q', '')
        
        # Carica il testo della domanda
        question_data = load_response("Plain-LLM", q_num)
        question_text = question_data['QuestionText'] if question_data else "Question text not available"
        
        # Filtra le valutazioni per questa domanda
        question_evals = eval_with_users[eval_with_users['question_id'] == question_id]
        
        if question_evals.empty:
            continue
        
        with st.expander(f"🔍 {question_id}: {question_text[:100]}{'...' if len(question_text) > 100 else ''}", expanded=False):
            
            # === Statistiche generali per la domanda ===
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📈 Question Statistics")
                
                # Metriche base
                total_evals = len(question_evals)
                unique_evaluators = question_evals['user_id'].nunique()
                agents_evaluated = question_evals['agent'].nunique()
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Evaluations", total_evals)
                with col_b:
                    st.metric("Evaluators", unique_evaluators)
                with col_c:
                    st.metric("Agents", agents_evaluated)
                
                # Distribuzione per ruolo (se disponibile)
                if 'role' in question_evals.columns and not question_evals['role'].isna().all():
                    st.markdown("**Evaluators by Role:**")
                    role_counts = question_evals['role'].value_counts()
                    for role, count in role_counts.items():
                        st.markdown(f"- {role}: {count}")
                
                # Distribuzione per istituto (se disponibile)
                if 'institution' in question_evals.columns and not question_evals['institution'].isna().all():
                    st.markdown("**Top Institutions:**")
                    inst_counts = question_evals['institution'].value_counts().head(5)
                    for inst, count in inst_counts.items():
                        if pd.notna(inst) and inst.strip():
                            st.markdown(f"- {inst}: {count}")
            
            with col2:
                st.subheader("🎯 Average Scores Radar")
                
                # Calcola le medie per agente per questa domanda
                agent_means = question_evals.groupby('agent')[numeric_cols].mean()
                
                if not agent_means.empty:
                    # Crea radar plot
                    fig_radar = go.Figure()
                    
                    categories = ['Relevance', 'Credibility', 'Uncertainty', 'Actionability']
                    colors = px.colors.qualitative.Set1
                    
                    for i, agent in enumerate(agent_means.index):
                        values = [agent_means.loc[agent, col] for col in numeric_cols]
                        
                        fig_radar.add_trace(go.Scatterpolar(
                            r=values,
                            theta=categories,
                            fill='toself',
                            name=agent,
                            line_color=colors[i % len(colors)]
                        ))
                    
                    fig_radar.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[0, 10],
                                tickvals=[0, 2, 4, 6, 8, 10]
                            )
                        ),
                        showlegend=True,
                        height=400,
                        title=f"Average Scores for {question_id}"
                    )
                    
                    st.plotly_chart(fig_radar, use_container_width=True)
            
            st.markdown("---")
            
            # === Dettagli per agente ===
            st.subheader("🤖 Agent Details & Responses")
            
            agents = question_evals['agent'].unique()
            
            for agent in sorted(agents):
                agent_evals = question_evals[question_evals['agent'] == agent]
                
                # Carica la risposta dell'agente
                agent_response = load_response(agent, q_num)
                
                with st.expander(f"🤖 {agent} ({len(agent_evals)} evaluations)", expanded=False):
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        # Mostra la risposta dell'agente
                        if agent_response and 'ResponseText' in agent_response:
                            st.markdown("**AI Response:**")
                            
                            # Dividi in sezioni per una migliore leggibilità
                            sections = split_sections(agent_response['ResponseText'])
                            
                            if sections:
                                for section_name, section_content in sections.items():
                                    if section_content.strip():
                                        st.markdown(f"**{section_name}:**")
                                        st.markdown(section_content.strip())
                                        st.markdown("")
                            else:
                                # Se non ci sono sezioni, mostra tutto il testo
                                with st.container(border=True):
                                    st.markdown(agent_response['ResponseText'])
                        else:
                            st.warning(f"Response not found for {agent}")
                    
                    with col2:
                        # Statistiche delle valutazioni per questo agente
                        st.markdown("**Evaluation Statistics:**")
                        
                        # Medie per criterio
                        means = agent_evals[numeric_cols].mean()
                        stds = agent_evals[numeric_cols].std()
                        
                        for col in numeric_cols:
                            mean_val = means[col] if not pd.isna(means[col]) else 0
                            std_val = stds[col] if not pd.isna(stds[col]) else 0
                            st.metric(
                                f"{col.title()}", 
                                f"{mean_val:.2f}", 
                                delta=f"±{std_val:.2f}"
                            )
                        
                        # Distribuzione dei voti
                        st.markdown("**Score Distributions:**")
                        for col in numeric_cols:
                            if not agent_evals[col].isna().all():
                                values = agent_evals[col].dropna()
                                if len(values) > 0:
                                    st.markdown(f"*{col.title()}:* {values.min():.0f}-{values.max():.0f} (n={len(values)})")
                        
                        # Lista dei valutatori
                        st.markdown("**Evaluators:**")
                        evaluator_info = []
                        for _, row in agent_evals.iterrows():
                            role = row.get('role', 'Unknown')
                            institution = row.get('institution', 'Unknown')
                            evaluator_info.append(f"- {role} ({institution})")
                        
                        # Mostra solo i primi 5 per risparmiare spazio
                        for info in evaluator_info[:5]:
                            st.markdown(info)
                        
                        if len(evaluator_info) > 5:
                            st.markdown(f"... and {len(evaluator_info) - 5} more")

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.info("Make sure the Google Sheets are properly configured and accessible.")
