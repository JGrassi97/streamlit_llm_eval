import streamlit as st

st.set_page_config(page_title="climaiscore", layout="wide")

# Hero
st.title("AI for Climate Information – Expert Evaluation")
st.caption("Evaluate AI-generated answers to climate adaptation questions.")

st.markdown("---")

with st.container(border=1):
	st.subheader("Purpose")
	st.markdown(
		"""
This evaluation is part of a research effort to understand how Large Language Models (LLMs) perform when providing
climate adaptation–related information. We focus on four quality dimensions that are critical for scientific and
applied use:

1. **Relevance** – Does the answer address the question directly and completely?
2. **Credibility** – Is the content scientifically sound and plausible?
3. **Uncertainty communication** – Are limitations, assumptions, or degrees of confidence stated clearly?
4. **Actionability** – Is the information useful for informing adaptation planning or decisions?

No personal data is required. Individual ratings are anonymized and only analyzed in aggregate.
		"""
	)

st.markdown("---")



with st.container(border=1):
	st.subheader("Evaluation format")
	st.markdown(
		"""
Each task shows **one question** and **two independent AI-generated answers** (A and B). The model identities are hidden.

For each answer you assign four separate scores (1–10) — you do **not** pick a winner and you should not force one answer to be higher if both (or neither) deserve it.

Pairs are randomized. You may encounter the same question again with a different combination of models; please rate independently each time.
		"""
	)

st.markdown("---")

with st.container(border=1):
	st.subheader("How to rate")
	st.markdown(
		"""
Please focus strictly on the four defined criteria. Do **not** try to do exhaustive fact checking or detect AI model identity.
If a response includes a claim you suspect *might* be wrong but you are not sure, do **not** penalize heavily unless it clearly undermines credibility in context.

### 1. Relevance (1–10)
How directly and completely does the answer address the question?
- 1–3 = Largely off-topic or misses key intent
- 4–6 = Partially addresses the question; gaps or unnecessary digressions
- 7–8 = Mostly focused and covers main aspects
- 9–10 = Fully focused, concise, and covers all essential aspects

Ignore: stylistic verbosity if content is on point; minor ordering differences.

### 2. Credibility (1–10)
Is the information scientifically plausible and consistent with established understanding? You are *not* asked to verify every fact; use domain judgement.
- 1–3 = Contains clear inaccuracies / misleading framing
- 4–6 = Mixed: plausible core but some weak / vague / slightly dubious parts
- 7–8 = Generally sound and reasonable
- 9–10 = Scientifically robust, well-framed, internally consistent

Do not down-rate solely because no citations are given (citations are not required). Penalize only for substantive scientific weakness, not style.

### 3. Uncertainty communication (1–10)
Does the answer appropriately communicate limits, assumptions, variability, or confidence—*only where relevant*?
- 1–3 = No acknowledgment of uncertainty where it clearly matters OR misleading certainty
- 4–6 = Some generic caveats; limited specificity
- 7–8 = Clear, context-aware indication of limits or ranges
- 9–10 = Precise, proportionate communication of uncertainty without overloading the reader

Do not punish an answer for brevity if the question is straightforward and uncertainty is minimal.

### 4. Actionability (1–10)
Does the answer provide information that can inform practical climate adaptation reasoning, planning, screening, or decisions?
- 1–3 = Abstract / generic; no usable guidance
- 4–6 = Some practical elements but fragmented or vague
- 7–8 = Provides concrete, context-relevant indications
- 9–10 = Offers clear, structured, decision-supportive guidance

High actionability does *not* require length—clarity and applicability matter more than volume.

### What NOT to do
- Do not score based on writing style elegance alone.
- Do not attempt to identify the model behind the answer.
- Do not harshly penalize absent citations unless factual plausibility is compromised.
- Do not give higher scores just because an answer is longer.

### If both answers are weak
You can give low scores to both. Scores are *independent per answer*; do not “force” a spread.

### If both are strong
You can give both high scores (e.g., 8–9). Only reserve 10 for truly exemplary performance.
		"""
	)

st.markdown("---")



