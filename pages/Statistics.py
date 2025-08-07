import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import gspread
from google.oauth2.service_account import Credentials
import os
import glob
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.linear_model import LinearRegression

# Set page config
st.set_page_config(layout="wide", page_title="Statistics - AI Climate Evaluation")

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

# === Main UI ===
st.title("📊 Evaluation Statistics")
st.success("✅ Authenticated successfully")

# Logout button
if st.button("🚪 Logout"):
    st.session_state["password_correct"] = False
    st.rerun()

st.markdown("---")

# Carica i dati
try:
    eval_df = load_evaluation_data()
    user_df = load_user_data()
    
    if eval_df.empty:
        st.info("No evaluation data available yet.")
        st.stop()
    
    # Converte le colonne numeriche per dati umani
    numeric_cols = ['relevance', 'credibility', 'uncertainty', 'actionability']
    for col in numeric_cols:
        if col in eval_df.columns:
            eval_df[col] = pd.to_numeric(eval_df[col], errors='coerce')
    
    # === Metriche generali ===
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Evaluations", len(eval_df))
    
    with col2:
        unique_users = eval_df['user_id'].nunique()
        st.metric("Active Evaluators", unique_users)
    
    with col3:
        unique_questions = eval_df['question_id'].nunique()
        st.metric("Questions Evaluated", unique_questions)
    
    with col4:
        unique_agents = eval_df['agent'].nunique()
        st.metric("AI Agents Compared", unique_agents)
    
    st.markdown("---")
    
    # === Analisi per Agent ===
    st.header("🤖 Performance by AI Agent")
    
    # Calcola medie per agent
    agent_stats = eval_df.groupby('agent')[numeric_cols].agg(['mean', 'std', 'count']).round(2)
    
    # Grafico a radar per confronto agent
    fig_radar = go.Figure()
    
    agents = eval_df['agent'].unique()
    categories = ['Relevance', 'Credibility', 'Uncertainty', 'Actionability']
    
    for agent in agents:
        agent_data = eval_df[eval_df['agent'] == agent]
        values = [agent_data[col].mean() for col in numeric_cols]
        
        fig_radar.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=agent,
            line_color=px.colors.qualitative.Set1[list(agents).index(agent) % len(px.colors.qualitative.Set1)]
        ))
    
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10]  # Cambiato per la nuova scala 1-10
            )),
        showlegend=True,
        title="Average Scores by AI Agent",
        height=500
    )
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.plotly_chart(fig_radar, use_container_width=True)
    
    with col2:
        st.subheader("Summary Table")
        # Tabella riassuntiva
        summary_table = eval_df.groupby('agent')[numeric_cols].mean().round(2)
        summary_table['Count'] = eval_df.groupby('agent').size()
        st.dataframe(summary_table, use_container_width=True)
    
    st.markdown("---")
    
    # === Distribuzione dei punteggi ===
    st.header("📈 Score Distribution")
    
    # Box plot per ogni criterio
    fig_box = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Relevance", "Credibility", "Uncertainty", "Actionability")
    )
    
    positions = [(1, 1), (1, 2), (2, 1), (2, 2)]
    
    for i, col in enumerate(numeric_cols):
        row, col_pos = positions[i]
        for agent in agents:
            agent_data = eval_df[eval_df['agent'] == agent][col].dropna()
            fig_box.add_trace(
                go.Box(y=agent_data, name=agent, showlegend=(i == 0)),
                row=row, col=col_pos
            )
    
    fig_box.update_layout(height=600, title_text="Score Distribution by Criterion and Agent")
    st.plotly_chart(fig_box, use_container_width=True)
    
    st.markdown("---")
    
    # === Analisi degli utenti ===
    st.header("👥 Evaluator Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Distribuzione valutazioni per utente
        user_counts = eval_df['user_id'].value_counts().head(10)
        fig_users = px.bar(
            x=user_counts.values,
            y=user_counts.index,
            orientation='h',
            title="Top 10 Most Active Evaluators",
            labels={'x': 'Number of Evaluations', 'y': 'User ID'}
        )
        st.plotly_chart(fig_users, use_container_width=True)
    
    with col2:
        # Distribuzione per ruolo (se disponibile)
        if not user_df.empty and 'role' in user_df.columns:
            role_counts = user_df['role'].value_counts()
            fig_roles = px.pie(
                values=role_counts.values,
                names=role_counts.index,
                title="Evaluators by Role"
            )
            st.plotly_chart(fig_roles, use_container_width=True)
    
    st.markdown("---")
    
    # === Matrice di correlazione ===
    st.header("🔗 Correlation Analysis")
    
    # Calcola correlazioni tra i criteri
    corr_matrix = eval_df[numeric_cols].corr()
    
    fig_corr = px.imshow(
        corr_matrix,
        text_auto=True,
        aspect="auto",
        title="Correlation Matrix between Evaluation Criteria",
        color_continuous_scale="RdBu_r"
    )
    
    st.plotly_chart(fig_corr, use_container_width=True)
    
    st.markdown("---")
    
    # === Analisi temporale (se disponibile timestamp) ===
    if 'timestamp' in eval_df.columns:
        st.header("⏰ Temporal Analysis")
        
        eval_df['timestamp'] = pd.to_datetime(eval_df['timestamp'])
        daily_counts = eval_df.groupby(eval_df['timestamp'].dt.date).size()
        
        fig_temporal = px.line(
            x=daily_counts.index,
            y=daily_counts.values,
            title="Daily Evaluation Activity",
            labels={'x': 'Date', 'y': 'Number of Evaluations'}
        )
        
        st.plotly_chart(fig_temporal, use_container_width=True)
    
    # === Sezione dati raw (opzionale) ===
    with st.expander("🔍 Raw Data Preview"):
        st.subheader("Recent Evaluations")
        st.dataframe(eval_df.head(20), use_container_width=True)
        
        st.subheader("Download Data")
        csv = eval_df.to_csv(index=False)
        st.download_button(
            label="Download evaluation data as CSV",
            data=csv,
            file_name="evaluation_data.csv",
            mime="text/csv"
        )

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.info("Make sure the Google Sheets are properly configured and accessible.")


