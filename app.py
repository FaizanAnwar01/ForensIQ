"""
ForensIQ – Streamlit Dashboard
================================
Run with:  streamlit run app.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import streamlit as st
import pandas as pd

from agent import ForensIQAgent
from utils import extract_text_from_file

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="ForensIQ - AI Forensic Analyst",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Load custom CSS
# ---------------------------------------------------------------------------
_CSS_PATH = Path(__file__).resolve().parent / "styles.css"
if _CSS_PATH.exists():
    st.markdown(f"<style>{_CSS_PATH.read_text()}</style>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
if "agent" not in st.session_state:
    try:
        st.session_state.agent = ForensIQAgent()
        st.session_state.init_error = None
    except Exception as exc:
        st.session_state.agent = None
        st.session_state.init_error = str(exc)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = {
        "contradictions": None,
        "timeline": None,
        "profiles": None,
        "next_questions": None,
    }

agent: ForensIQAgent | None = st.session_state.agent


# ---------------------------------------------------------------------------
# Helper – render badge HTML
# ---------------------------------------------------------------------------
def _badge(text: str, variant: str = "medium") -> str:
    return f'<span class="badge badge-{variant}">{text}</span>'


def _render_error(result: dict | list) -> bool:
    """If result is a dict with an 'error' key, show it and return True."""
    if isinstance(result, dict) and "error" in result:
        st.error(result["error"])
        if "raw_response" in result:
            with st.expander("Raw LLM response (debug)"):
                st.code(result["raw_response"], language="text")
        return True
    return False


# ---------------------------------------------------------------------------
# SIDEBAR – Case Management
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Case Management")

    if st.session_state.init_error:
        st.error(f"Agent init failed: {st.session_state.init_error}")
        st.info("Check your .env file and API key.")
        st.stop()

    # ── Document label ───────────────────────────────────────────────
    doc_label = st.text_input(
        "Document label",
        placeholder='e.g. "Suspect A – Statement 1"',
        key="doc_label",
    )

    # ── Text input ───────────────────────────────────────────────────
    raw_text = st.text_area(
        "Paste raw statement / transcript",
        height=180,
        placeholder="Paste suspect statements, witness testimony, or case notes here...",
        key="raw_text",
    )

    # ── File upload ──────────────────────────────────────────────────
    uploaded_file = st.file_uploader(
        "Or upload a file",
        type=["txt", "pdf", "docx"],
        key="file_upload",
    )

    # ── Add to memory button ─────────────────────────────────────────
    if st.button("Add to Case Memory", use_container_width=True, type="primary"):
        text_to_add = ""
        label = doc_label.strip() or f"Document {len(agent.memory) + 1}"

        if uploaded_file is not None:
            try:
                text_to_add = extract_text_from_file(uploaded_file)
            except Exception as exc:
                st.error(f"File parse error: {exc}")

        if raw_text.strip():
            text_to_add = (text_to_add + "\n\n" + raw_text.strip()).strip()

        if text_to_add:
            agent.add_document(label, text_to_add)
            st.success(f"Added: {label}")
            st.rerun()
        else:
            st.warning("No text provided. Paste text or upload a file.")

    st.divider()

    # ── Memory display ───────────────────────────────────────────────
    st.markdown("### Case Memory")
    memory = agent.memory
    if memory:
        st.caption(f"{len(memory)} document(s) loaded")
        for idx, doc in enumerate(memory):
            with st.expander(f"{doc['label']}", expanded=False):
                st.text(doc["text"][:800] + ("..." if len(doc["text"]) > 800 else ""))
                if st.button("Remove", key=f"rm_{idx}"):
                    agent.remove_document(idx)
                    st.rerun()
    else:
        st.caption("No documents loaded yet.")

    st.divider()
    if st.button("Clear All Memory", use_container_width=True):
        agent.clear_memory()
        st.session_state.chat_history = []
        st.session_state.analysis_results = {k: None for k in st.session_state.analysis_results}
        st.rerun()


# ---------------------------------------------------------------------------
# MAIN – Header
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="forensiq-header">'
    "<h1>ForensIQ - AI Forensic Analyst</h1>"
    "<p>AI-powered forensic text analysis for criminal case investigation</p>"
    "</div>",
    unsafe_allow_html=True,
)

# ── Top stats row ────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        f'<div class="stat-box"><div class="stat-value">{len(agent.memory)}</div>'
        f'<div class="stat-label">Documents</div></div>',
        unsafe_allow_html=True,
    )
with c2:
    contra = st.session_state.analysis_results["contradictions"]
    n = len(contra) if isinstance(contra, list) else 0
    st.markdown(
        f'<div class="stat-box"><div class="stat-value">{n}</div>'
        f'<div class="stat-label">Contradictions</div></div>',
        unsafe_allow_html=True,
    )
with c3:
    profs = st.session_state.analysis_results["profiles"]
    n = len(profs) if isinstance(profs, list) else 0
    st.markdown(
        f'<div class="stat-box"><div class="stat-value">{n}</div>'
        f'<div class="stat-label">Profiles</div></div>',
        unsafe_allow_html=True,
    )
with c4:
    tl = st.session_state.analysis_results["timeline"]
    n = len(tl) if isinstance(tl, list) else 0
    st.markdown(
        f'<div class="stat-box"><div class="stat-value">{n}</div>'
        f'<div class="stat-label">Events</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("")  # spacer

# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Contradictions",
    "Timeline",
    "Suspect Profiles",
    "Next Questions",
    "Case Chat",
])

# ── TAB 1 – Contradictions ───────────────────────────────────────────────
with tab1:
    st.subheader("Contradiction Detector")
    st.caption("Cross-references all statements in memory to flag logical inconsistencies.")

    if st.button("Run Contradiction Analysis", key="run_contra", type="primary"):
        if not agent.memory:
            st.warning("Add at least one document to case memory first.")
        else:
            with st.spinner("Analyzing statements for contradictions..."):
                result = agent.detect_contradictions()
            st.session_state.analysis_results["contradictions"] = result
            st.rerun()

    data = st.session_state.analysis_results["contradictions"]
    if data is not None:
        if _render_error(data):
            pass
        elif isinstance(data, list) and len(data) == 0:
            st.info("No contradictions detected in the current case documents.")
        elif isinstance(data, list):
            for i, item in enumerate(data, 1):
                st.markdown(
                    f'<div class="analysis-card contradiction">'
                    f'<strong>Contradiction #{i}</strong><br><br>'
                    f'<div class="profile-field"><div class="profile-field-label">Statement 1</div>'
                    f'<div class="profile-field-value">{item.get("statement_1", "N/A")}</div></div>'
                    f'<div class="profile-field"><div class="profile-field-label">Statement 2</div>'
                    f'<div class="profile-field-value">{item.get("statement_2", "N/A")}</div></div>'
                    f'<div class="profile-field"><div class="profile-field-label">Conflict Explanation</div>'
                    f'<div class="profile-field-value">{item.get("explanation_of_conflict", "N/A")}</div></div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
            # Download
            st.download_button(
                "Download Contradictions (JSON)",
                json.dumps(data, indent=2),
                "contradictions.json",
                "application/json",
            )

# ── TAB 2 – Timeline ────────────────────────────────────────────────────
with tab2:
    st.subheader("Timeline Constructor")
    st.caption("Extracts temporal data and assembles a chronological sequence of events.")

    if st.button("Build Timeline", key="run_tl", type="primary"):
        if not agent.memory:
            st.warning("Add at least one document to case memory first.")
        else:
            with st.spinner("Extracting and ordering temporal events..."):
                result = agent.build_timeline()
            st.session_state.analysis_results["timeline"] = result
            st.rerun()

    data = st.session_state.analysis_results["timeline"]
    if data is not None:
        if _render_error(data):
            pass
        elif isinstance(data, list) and len(data) == 0:
            st.info("No temporal data found in the current case documents.")
        elif isinstance(data, list):
            df = pd.DataFrame(data)
            display_cols = [c for c in ["timestamp", "event_description", "source", "confidence_level"] if c in df.columns]
            if display_cols:
                st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button(
                "Download Timeline (JSON)",
                json.dumps(data, indent=2),
                "timeline.json",
                "application/json",
            )

# ── TAB 3 – Suspect Profiles ────────────────────────────────────────────
with tab3:
    st.subheader("Suspect Profiler")
    st.caption("Builds comprehensive profile cards for every individual mentioned in the case.")

    if st.button("Generate Profiles", key="run_prof", type="primary"):
        if not agent.memory:
            st.warning("Add at least one document to case memory first.")
        else:
            with st.spinner("Building suspect and witness profiles..."):
                result = agent.profile_suspects()
            st.session_state.analysis_results["profiles"] = result
            st.rerun()

    data = st.session_state.analysis_results["profiles"]
    if data is not None:
        if _render_error(data):
            pass
        elif isinstance(data, list) and len(data) == 0:
            st.info("No named individuals found in the current case documents.")
        elif isinstance(data, list):
            for profile in data:
                role = profile.get("role_in_case", "unknown").lower()
                badge_class = "suspect" if "suspect" in role else ("witness" if "witness" in role else "victim")

                with st.expander(f"{profile.get('name', 'Unknown')}  —  {role.title()}", expanded=True):
                    st.markdown(_badge(role, badge_class), unsafe_allow_html=True)
                    st.markdown("")

                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**Potential Motives**")
                        motives = profile.get("potential_motives", [])
                        if motives and motives != ["none identified"]:
                            for m in motives:
                                st.markdown(f"- {m}")
                        else:
                            st.caption("None identified")

                        st.markdown("**Behavioral Flags**")
                        flags = profile.get("behavioral_flags", [])
                        if flags and flags != ["none identified"]:
                            for f in flags:
                                st.markdown(f"- {f}")
                        else:
                            st.caption("None identified")

                    with col_b:
                        st.markdown("**Key Statements**")
                        stmts = profile.get("key_statements", [])
                        for s in stmts[:5]:
                            st.markdown(f'> {s}')

                        st.markdown("**Timeline Presence**")
                        tp = profile.get("timeline_presence", [])
                        for t in tp[:5]:
                            st.markdown(f"- {t}")

                    assoc = profile.get("known_associations", [])
                    if assoc:
                        st.markdown("**Known Associations**")
                        st.markdown(", ".join(assoc))

            st.download_button(
                "Download Profiles (JSON)",
                json.dumps(data, indent=2),
                "profiles.json",
                "application/json",
            )

# ── TAB 4 – Next Questions ──────────────────────────────────────────────
with tab4:
    st.subheader("Next-Question Generator")
    st.caption("Identifies gaps and suggests the most critical follow-up interrogation questions.")

    if st.button("Generate Questions", key="run_nq", type="primary"):
        if not agent.memory:
            st.warning("Add at least one document to case memory first.")
        else:
            with st.spinner("Analyzing gaps and generating follow-up questions..."):
                result = agent.generate_next_questions()
            st.session_state.analysis_results["next_questions"] = result
            st.rerun()

    data = st.session_state.analysis_results["next_questions"]
    if data is not None:
        if _render_error(data):
            pass
        elif isinstance(data, list) and len(data) == 0:
            st.info("No information gaps detected – case data appears complete.")
        elif isinstance(data, list):
            for i, q in enumerate(data, 1):
                iv = q.get("investigative_value", "medium").lower()
                st.markdown(
                    f'<div class="analysis-card question">'
                    f'<strong>Q{i}. {q.get("suggested_question", "N/A")}</strong><br>'
                    f'{_badge(iv, iv)}&nbsp;&nbsp;'
                    f'<span style="color:var(--forensiq-text-dim);font-size:0.85rem;">'
                    f'Target: {q.get("target_person", "N/A")}</span><br><br>'
                    f'<div class="profile-field-label">Reasoning</div>'
                    f'<div class="profile-field-value">{q.get("reasoning", "N/A")}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
            st.download_button(
                "Download Questions (JSON)",
                json.dumps(data, indent=2),
                "next_questions.json",
                "application/json",
            )

# ── TAB 5 – Case Chat ───────────────────────────────────────────────────
with tab5:
    st.subheader("Case Chat")
    st.caption("Ask free-form questions about the loaded case documents.")

    if not agent.memory:
        st.info("Add documents to case memory to start chatting.")
    else:
        # Render history
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input
        if user_input := st.chat_input("Ask about the case..."):
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    reply = agent.chat(user_input)
                st.markdown(reply)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})

        if st.session_state.chat_history:
            if st.button("Clear Chat History", key="clear_chat"):
                st.session_state.chat_history = []
                agent.reset_chat()
                st.rerun()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="forensiq-footer">'
    "ForensIQ v1.0 | Developed by <strong>ForensIQ Team </strong> "
    "(Faizan, Shoaib, Burhan) | "
    "University of Engineering and Technology, Taxila — AI Project"
    "</div>",
    unsafe_allow_html=True,
)
