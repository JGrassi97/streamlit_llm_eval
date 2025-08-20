import streamlit as st

st.set_page_config(page_title="AI for Climate Adaptation – Evaluation", layout="wide")

# Hero
st.title("AI for Climate Adaptation – Evaluation Platform")
st.caption("Evaluate AI-generated answers to climate adaptation questions.")

st.markdown("---")

# Three quick sections
col1, col2, col3 = st.columns(3)
with col1:
   with st.container(border=True):
      st.subheader("What you'll do")
      st.markdown(
         "- Read a question\n"
         "- Compare 2 anonymous AI answers\n"
         "- Score each answer (1–10)"
      )
with col2:
   with st.container(border=True):
      st.subheader("Scoring criteria")
      st.markdown(
         "- Relevance\n"
         "- Credibility\n"
         "- Uncertainty communication\n"
         "- Actionability"
      )
with col3:
   with st.container(border=True):
      st.subheader("Time & commitment")
      st.markdown(
         "- ~2–3 minutes per question\n"
         "- Stop anytime"
      )

st.markdown("---")

# How to start
left, mid, right = st.columns([1, 2, 1])
with mid:
   with st.container(border=True):
      st.subheader("Start here")
      st.markdown(
         "- Open the 'Evaluation' page from the sidebar.\n"
         "- Enter a username. If it's your first time, you can optionally share some profile info.\n"
         "- Keep your username to return later."
      )
      st.write("")
      # Primary CTA
      if hasattr(st, "page_link"):
         st.page_link("pages/Evaluation.py", label="Start Evaluation", icon="➡️")
      else:
         if st.button("Start Evaluation", type="primary", use_container_width=True):
            try:
               st.switch_page("pages/Evaluation.py")
            except Exception:
               st.info("Use the left sidebar to open 'Evaluation'.")

# Privacy/info
st.info(
   "Why a username? We use it to count evaluations and associate sessions. "
   "Your ratings remain anonymous and are only analyzed in aggregate. "
   "No personal data is required."
)

 
