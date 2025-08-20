import streamlit as st

st.set_page_config(page_title="AI for Climate Adaptation – Evaluation", layout="wide")

st.title("AI for Climate Adaptation – Evaluation Platform")

st.markdown("""
Obiettivo
- Valutare risposte generate da diversi modelli LLM su domande di adattamento climatico.

Cosa farai
- Leggere una domanda e confrontare 2 risposte anonime.
- Valutare ciascuna risposta (scala 1–10) su:
   - Relevance (rilevanza)
   - Credibility (accuratezza scientifica)
   - Uncertainty communication (chiarezza su limiti/incertezza)
   - Actionability (utilità per decisioni/azione)

Come accedere
- Apri la pagina "Evaluation" dal menu laterale.
- Inserisci uno username. Se è la prima volta, puoi (facoltativo) indicare alcune info di profilo.
- Conserva lo username: servirà per continuare in futuro.

Tempo richiesto
- 2–3 minuti per domanda. Puoi interrompere in qualsiasi momento.

Dati e privacy
- Lo username serve a conteggiare le valutazioni e associare le sessioni.
- Le valutazioni sono anonime e analizzate in forma aggregata.
- Nessun dato personale è obbligatorio.

Per iniziare
- Vai a "Evaluation" nella sidebar e inizia la valutazione.
""")
 
