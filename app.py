"""
UK CV Tailor — Streamlit app.

Flow:
  1. Paste/upload your MASTER CV + the job description.
  2. Tailor → first-pass CV + match score.
  3. Smart Questions → interactive questionnaire (hidden matches, fast-learnable
     skills with learn-time estimates, genuine gaps). Answer with buttons.
  4. Apply answers → re-tailored CV that truthfully reflects your choices.
  5. Roadmap → free learning plan for the skills you don't yet have.

Run:  streamlit run app.py
"""

import streamlit as st

from extract import extract_text
from llm import (
    tailor_cv, score_cv, analyse_gaps, build_roadmap, refine_with_answers,
)
from renderers import to_markdown, to_docx, to_pdf

st.set_page_config(page_title="UK CV Tailor", page_icon="📄", layout="wide")
st.title("📄 UK CV Tailor — ATS-friendly")
st.caption(
    "Paste your master CV and a job description. Get a tailored, ATS-ready CV, "
    "a match score, smart gap questions, and a free learning roadmap."
)


# --------------------------------------------------------------------------- #
# Cached wrappers — identical inputs return instantly without a new API call.
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def cached_tailor(job_description: str, current_cv: str) -> dict:
    return tailor_cv(job_description, current_cv)


@st.cache_data(show_spinner=False)
def cached_score(job_description: str, tailored_markdown: str) -> dict:
    return score_cv(job_description, tailored_markdown)


@st.cache_data(show_spinner=False)
def cached_gaps(job_description: str, master_cv: str, tailored_markdown: str) -> dict:
    return analyse_gaps(job_description, master_cv, tailored_markdown)


@st.cache_data(show_spinner=False)
def cached_roadmap(job_description: str, skills_context: str, missing_skills: str) -> dict:
    return build_roadmap(job_description, skills_context, missing_skills)


@st.cache_data(show_spinner=False)
def cached_refine(job_description: str, current_cv: str, answers_context: str) -> dict:
    return refine_with_answers(job_description, current_cv, answers_context)


@st.cache_data(show_spinner=False)
def cached_extract(file_bytes: bytes, filename: str) -> str:
    class _F:
        def __init__(self, b, n):
            self._b, self.name = b, n
        def read(self):
            return self._b
    return extract_text(_F(file_bytes, filename))


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
col1, col2 = st.columns(2)

with col1:
    st.subheader("Job Description")
    job_desc = st.text_area(
        "Paste the job ad",
        height=380,
        placeholder="Paste the full job description here...",
        label_visibility="collapsed",
    )

with col2:
    st.subheader("Your Master CV")
    uploaded = st.file_uploader(
        "Upload your master CV (PDF or DOCX) — or paste below",
        type=["pdf", "docx"],
    )
    cv_from_file = ""
    if uploaded is not None:
        try:
            cv_from_file = cached_extract(uploaded.getvalue(), uploaded.name)
            st.success(f"Extracted {len(cv_from_file)} characters from {uploaded.name}")
        except Exception as e:
            st.error(f"Couldn't read that file: {e}")

    master_cv = st.text_area(
        "Or paste your master CV",
        value=cv_from_file,
        height=260,
        placeholder="Paste your full master CV (everything you've done)...",
        label_visibility="collapsed",
    )


# --------------------------------------------------------------------------- #
# Action: first tailoring pass
# --------------------------------------------------------------------------- #
ready = bool(job_desc.strip()) and bool(master_cv.strip())
if st.button("✨ Tailor my CV", type="primary", disabled=not ready):
    with st.spinner("Tailoring your CV (using Gemini 2.5 Pro)..."):
        try:
            cv = cached_tailor(job_desc, master_cv)
            st.session_state["cv"] = cv
            st.session_state["job_desc"] = job_desc
            st.session_state["master_cv"] = master_cv
            # clear downstream stale state
            for k in ("score", "gaps", "roadmap", "refined"):
                st.session_state.pop(k, None)
        except Exception as e:
            st.error(f"Something went wrong while tailoring: {e}")


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
if "cv" in st.session_state:
    # use the refined CV if the user has applied answers, else the first pass
    active_cv = st.session_state.get("refined", st.session_state["cv"])
    md = to_markdown(active_cv)
    jd = st.session_state["job_desc"]
    master = st.session_state["master_cv"]

    tabs = st.tabs(
        ["Preview", "Match Score", "Smart Questions", "Learning Roadmap", "Downloads", "Raw JSON"]
    )

    # ---------- Preview ----------
    with tabs[0]:
        if "refined" in st.session_state:
            st.info("Showing your refined CV (after applying your answers).")
        st.markdown(md)

    # ---------- Match Score ----------
    with tabs[1]:
        if st.button("Calculate / refresh match score"):
            with st.spinner("Scoring against the job description..."):
                try:
                    st.session_state["score"] = cached_score(jd, md)
                except Exception as e:
                    st.error(f"Scoring failed: {e}")

        if "score" in st.session_state:
            s = st.session_state["score"]
            m1, m2 = st.columns(2)
            m1.metric("Overall match", f"{s.get('overall_score', 0)}/100")
            m2.metric("Keyword coverage", f"{s.get('keyword_coverage', 0)}%")
            st.progress(min(max(s.get("overall_score", 0), 0), 100) / 100)

            if s.get("matched_keywords"):
                st.markdown("**✅ Matched keywords**")
                st.write(", ".join(s["matched_keywords"]))
            if s.get("missing_keywords"):
                st.markdown("**⚠️ Missing keywords**")
                st.write(", ".join(s["missing_keywords"]))
            for title, key in [("Strengths", "strengths"), ("Gaps", "gaps"), ("Suggestions", "suggestions")]:
                if s.get(key):
                    st.markdown(f"**{title}**")
                    for item in s[key]:
                        st.markdown(f"- {item}")

    # ---------- Smart Questions ----------
    with tabs[2]:
        st.markdown(
            "These questions look at your **whole master CV** versus the job, and find "
            "skills worth surfacing, things you could learn fast, and honest gaps. "
            "Answer them, then apply — only what you confirm gets added, truthfully."
        )
        if st.button("Generate smart questions"):
            with st.spinner("Analysing gaps against your full CV..."):
                try:
                    st.session_state["gaps"] = cached_gaps(jd, master, md)
                    st.session_state.pop("answers", None)
                except Exception as e:
                    st.error(f"Gap analysis failed: {e}")

        if "gaps" in st.session_state:
            gaps = st.session_state["gaps"]
            if gaps.get("summary"):
                st.info(gaps["summary"])

            answers = st.session_state.get("answers", {})
            type_label = {
                "hidden_match": "🟢 You likely already have this",
                "fast_learnable": "🟡 Learnable fast",
                "genuine_gap": "🔴 Genuine gap",
            }

            for q in gaps.get("questions", []):
                qid = q.get("id", q.get("skill", "q"))
                with st.container(border=True):
                    st.markdown(f"**{type_label.get(q.get('type'), '')} — {q.get('skill','')}**")
                    st.markdown(q.get("question", ""))
                    if q.get("context"):
                        st.caption(q["context"])
                    if q.get("learnability"):
                        st.caption(f"⏱️ {q['learnability']}")

                    labels = [o["label"] for o in q.get("options", [])]
                    # pre-select the recommended option
                    rec_idx = 0
                    for i, o in enumerate(q.get("options", [])):
                        if o.get("recommended"):
                            rec_idx = i
                            break
                    if labels:
                        choice = st.radio(
                            "Your choice",
                            labels,
                            index=rec_idx,
                            key=f"radio_{qid}",
                            label_visibility="collapsed",
                        )
                        chosen = next((o for o in q["options"] if o["label"] == choice), None)
                        answers[qid] = {
                            "skill": q.get("skill", ""),
                            "choice_label": choice,
                            "choice_value": chosen.get("value", "") if chosen else "",
                            "suggested_cv_line": q.get("suggested_cv_line", ""),
                            "type": q.get("type", ""),
                        }
                    if q.get("suggested_cv_line"):
                        st.caption(f"📝 If added: \"{q['suggested_cv_line']}\"")

            st.session_state["answers"] = answers

            if st.button("✅ Apply my answers and re-tailor", type="primary"):
                # build a truthful instruction block from the answers
                lines = []
                for a in answers.values():
                    label = a["choice_label"].lower()
                    # skip explicit opt-outs
                    if any(x in label for x in ["no /", "leave it out", "don't add", "do not add", "skip"]):
                        continue
                    line = a["suggested_cv_line"] or a["skill"]
                    framing = a["choice_value"] or a["choice_label"]
                    lines.append(f"- {a['skill']}: {framing}. Suggested wording: {line}")
                answers_context = "\n".join(lines) if lines else "No additional items confirmed."
                with st.spinner("Re-tailoring with your confirmed answers..."):
                    try:
                        st.session_state["refined"] = cached_refine(jd, master, answers_context)
                        st.session_state.pop("score", None)  # force rescore on new CV
                        st.success("Done — check the Preview and Downloads tabs.")
                    except Exception as e:
                        st.error(f"Re-tailoring failed: {e}")

    # ---------- Learning Roadmap ----------
    with tabs[3]:
        st.markdown(
            "A focused, mostly-**free** plan to get interview-ready on the skills this job "
            "wants that you don't yet have. Honest about effort — and what you can learn fast."
        )
        if st.button("Build my learning roadmap"):
            # pull missing skills from the score if present, else ask the model fresh
            missing = ""
            if "score" in st.session_state:
                missing = ", ".join(st.session_state["score"].get("missing_keywords", []))
            if not missing:
                missing = "Infer the missing skills from the job description versus the CV."
            skills_context = ", ".join(active_cv.get("skills", [])) or master[:2000]
            with st.spinner("Building your roadmap with free resources..."):
                try:
                    st.session_state["roadmap"] = cached_roadmap(jd, skills_context, missing)
                except Exception as e:
                    st.error(f"Roadmap failed: {e}")

        if "roadmap" in st.session_state:
            rm = st.session_state["roadmap"]
            if rm.get("overview"):
                st.info(rm["overview"])
            prio_badge = {"high": "🔴 High", "medium": "🟡 Medium", "low": "🟢 Low"}
            for item in rm.get("items", []):
                with st.container(border=True):
                    st.markdown(
                        f"### {item.get('skill','')}  "
                        f"<span style='font-size:0.8em'>({prio_badge.get(item.get('priority',''),'')} · "
                        f"⏱️ {item.get('effort','')})</span>",
                        unsafe_allow_html=True,
                    )
                    if item.get("why"):
                        st.markdown(f"**Why it matters:** {item['why']}")
                    if item.get("leverage"):
                        st.markdown(f"**Your head start:** {item['leverage']}")
                    if item.get("steps"):
                        st.markdown("**Steps:**")
                        for i, step in enumerate(item["steps"], 1):
                            st.markdown(f"{i}. {step}")
                    if item.get("free_resources"):
                        st.markdown("**Free resources:**")
                        for r in item["free_resources"]:
                            st.markdown(f"- **{r.get('name','')}** ({r.get('type','')}) — {r.get('note','')}")
                    if item.get("interview_talking_point"):
                        st.success(f"💬 How to frame it honestly: {item['interview_talking_point']}")

    # ---------- Downloads ----------
    with tabs[4]:
        st.caption("Downloads use your refined CV if you've applied answers, else the first pass.")
        st.download_button("⬇️ Download Markdown", md, file_name="tailored_cv.md")
        st.download_button(
            "⬇️ Download DOCX",
            to_docx(active_cv),
            file_name="tailored_cv.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        st.download_button(
            "⬇️ Download PDF",
            to_pdf(active_cv),
            file_name="tailored_cv.pdf",
            mime="application/pdf",
        )

    # ---------- Raw JSON ----------
    with tabs[5]:
        st.json(active_cv)
