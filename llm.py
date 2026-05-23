"""
Gemini API calls for tailoring and scoring.

Uses the current `google-genai` SDK (the older `google-generativeai`
package is deprecated). Functions are kept pure so Streamlit's
@st.cache_data can wrap them safely in app.py.
"""

import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

from prompt import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    SCORE_SYSTEM_PROMPT,
    SCORE_USER_TEMPLATE,
    GAP_SYSTEM_PROMPT,
    GAP_USER_TEMPLATE,
    ROADMAP_SYSTEM_PROMPT,
    ROADMAP_USER_TEMPLATE,
)

load_dotenv()

_API_KEY = os.getenv("GEMINI_API_KEY")
_client = genai.Client(api_key=_API_KEY) if _API_KEY else None

# Best quality model. Flash is faster/cheaper if you hit rate limits —
# swap to "gemini-2.5-flash" if Pro's free-tier limits are too tight for you.
MODEL_NAME = "gemini-2.5-flash"
FAST_MODEL = "gemini-2.5-flash"  # used for lighter calls (scoring)


def _require_client():
    if _client is None:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to your .env file or Streamlit secrets."
        )
    return _client


def _clean_json(text: str) -> dict:
    """Parse JSON, stripping accidental markdown fences if the model adds them."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
        text = text.strip("` \n")
    return json.loads(text)


def _generate(model_name: str, system_prompt: str, user_prompt: str, temperature: float) -> dict:
    client = _require_client()
    response = client.models.generate_content(
        model=model_name,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=temperature,
        ),
    )
    return _clean_json(response.text)


def tailor_cv(job_description: str, current_cv: str) -> dict:
    """Send the JD + CV to Gemini and return structured tailored-CV JSON."""
    user_prompt = USER_PROMPT_TEMPLATE.format(
        job_description=job_description,
        current_cv=current_cv,
    )
    return _generate(MODEL_NAME, SYSTEM_PROMPT, user_prompt, 0.4)


def score_cv(job_description: str, tailored_cv_markdown: str) -> dict:
    """Second cheap call: grade how well the tailored CV matches the JD."""
    user_prompt = SCORE_USER_TEMPLATE.format(
        job_description=job_description,
        tailored_cv=tailored_cv_markdown,
    )
    return _generate(FAST_MODEL, SCORE_SYSTEM_PROMPT, user_prompt, 0.2)


def analyse_gaps(job_description: str, master_cv: str, tailored_cv_markdown: str) -> dict:
    """Build the interactive questionnaire: hidden matches, fast-learnable, genuine gaps."""
    user_prompt = GAP_USER_TEMPLATE.format(
        job_description=job_description,
        master_cv=master_cv,
        tailored_cv=tailored_cv_markdown,
    )
    return _generate(MODEL_NAME, GAP_SYSTEM_PROMPT, user_prompt, 0.3)


def build_roadmap(job_description: str, skills_context: str, missing_skills: str) -> dict:
    """Produce an honest, mostly-free learning roadmap for missing skills."""
    user_prompt = ROADMAP_USER_TEMPLATE.format(
        job_description=job_description,
        skills_context=skills_context,
        missing_skills=missing_skills,
    )
    return _generate(FAST_MODEL, ROADMAP_SYSTEM_PROMPT, user_prompt, 0.4)


def refine_with_answers(job_description: str, current_cv: str, answers_context: str) -> dict:
    """Re-tailor the CV, incorporating the candidate's questionnaire answers truthfully."""
    augmented = (
        current_cv
        + "\n\n--- ADDITIONAL CONFIRMED INFORMATION FROM THE CANDIDATE ---\n"
        + "Incorporate the following ONLY as truthfully framed below. Do not exaggerate "
        + "beyond what the candidate confirmed:\n"
        + answers_context
    )
    user_prompt = USER_PROMPT_TEMPLATE.format(
        job_description=job_description,
        current_cv=augmented,
    )
    return _generate(MODEL_NAME, SYSTEM_PROMPT, user_prompt, 0.4)
