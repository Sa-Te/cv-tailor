# UK CV Tailor 📄

A free, ATS-friendly CV tailoring tool. Paste a job description + your current CV,
and get back a CV rewritten for that specific role — in Markdown, DOCX, and PDF —
plus a match score that tells you what keywords you're missing.

Built with Streamlit + Google Gemini (free tier). No paid services required.

---

## What it does

1. You paste a job description and your **master CV** (or upload it as PDF/DOCX).
2. Gemini rewrites the CV tailored to the job, following UK ATS rules — without
   fabricating anything not in your original CV.
3. **Smart Questions**: a gap analysis compares your *whole* master CV to the job
   and asks tappable questions — surfacing skills you already have but buried,
   flagging skills you could learn fast (with honest learn-time estimates), and
   being straight about genuine gaps. Only what you confirm gets added, truthfully.
4. **Learning Roadmap**: a mostly-free study plan to get interview-ready on the
   skills you don't yet have, with real free resources and honest effort estimates.
5. You get a preview, three downloadable formats, and a match score.

> **On honesty:** the tool will not help you fake experience. For genuine domain
> gaps it points you to the roadmap instead of keyword-stuffing. That's deliberate —
> getting to interview on a lie tends to end at the interview.

---

## Setup (one time)

### 1. Get a free Gemini API key
Go to **https://aistudio.google.com/apikey**, sign in with a Google account,
and click **Create API key**. The free tier is plenty for personal use
(roughly 10 requests/min, a few hundred/day on Gemini 2.5 Flash).

### 2. Install Python 3.10+
Check with `python --version`. If you don't have it, get it from python.org.

### 3. Create a virtual environment and install dependencies
```bash
cd cv-tailor
python -m venv .venv

# Activate it:
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows (PowerShell)

pip install -r requirements.txt
```

### 4. Add your API key
```bash
cp .env.example .env
```
Then open `.env` and paste your key after `GEMINI_API_KEY=`.

---

## Run it

```bash
streamlit run app.py
```

Your browser opens at `http://localhost:8501`. That's the tool.

To stop it: `Ctrl+C` in the terminal. To run it again later, just re-activate
the venv (`source .venv/bin/activate`) and run the same command.

---

## How to use it

1. Paste the **job description** in the left box.
2. Either **upload your CV** (PDF/DOCX) or paste it as text on the right.
3. Click **Tailor my CV**.
4. Check the **Preview** tab, then the **Match Score** tab (click "Calculate
   match score"), then grab your files in **Downloads**.

> ⚠️ Always read the output before sending it anywhere. The tool is told never
> to invent facts, but you are responsible for what goes on your CV. Check every
> claim is true and the dates/companies are right.

---

## Deploy it for free (access from anywhere)

Streamlit Community Cloud hosts public apps for free.

1. **Push to GitHub.** Create a *public* repo and push these files.
   The `.gitignore` already excludes `.env` — your key will NOT be uploaded.
   Double-check it isn't committed: `git status` should not list `.env`.

2. **Deploy.** Go to **https://share.streamlit.io**, sign in with GitHub,
   click **New app**, pick your repo, and set the main file to `app.py`.

3. **Add your key as a secret.** In the app's settings → **Secrets**, add:
   ```toml
   GEMINI_API_KEY = "your_key_here"
   ```
   Streamlit exposes secrets as environment variables, so the existing
   `os.getenv("GEMINI_API_KEY")` in `llm.py` picks it up with no code change.

4. Deploy. You get a public URL like `your-app.streamlit.app`.

> Anyone with the URL can use the app and will be spending *your* Gemini free
> quota. For personal use, keep the URL private or add a simple password
> (Streamlit supports this via `st.secrets` + a password check).

---

## Customising the prompt (the biggest quality lever)

Open `prompt.py`. The `SYSTEM_PROMPT` controls everything about the output.
If you work in a specific field, add a few field-specific rules — e.g. for
software roles, "list the tech stack per role"; for project management,
"emphasise budget size, team size, and methodologies (Agile, PRINCE2)".

Workflow for improving it: run a real job ad through the tool, read the output
critically, find one thing that's wrong or weak, add a rule to fix it, repeat.
Two or three rounds gets you a noticeably better tool.

---

## File overview

| File              | What it does                                            |
|-------------------|---------------------------------------------------------|
| `app.py`          | Streamlit UI, file upload, caching, score panel         |
| `prompt.py`       | The system prompts — edit this to tune quality          |
| `llm.py`          | Gemini API calls (tailor + score)                       |
| `extract.py`      | Pulls text out of uploaded PDF/DOCX CVs                 |
| `renderers.py`    | Builds Markdown, DOCX, and PDF outputs                  |
| `requirements.txt`| Python dependencies                                     |
| `.env.example`    | Template for your API key                               |

---

## Troubleshooting

- **Stuck on a skeleton / grey loading screen (WSL)** — this is the #1 WSL issue.
  Two fixes, in order: (1) run with
  `streamlit run app.py --server.enableCORS false --server.enableXsrfProtection false --server.fileWatcherType none`,
  and (2) if that fails, copy the project off the Windows mount into native WSL
  (`cp -r /mnt/c/Users/<you>/Desktop/cv-tailor ~/cv-tailor && cd ~/cv-tailor`) and
  run it from there. Running from `/mnt/c/` is slow and breaks the file watcher.
  The `gio: ... Operation not supported` line is harmless — just open
  `http://localhost:8501` in your Windows browser manually.
- **Windows: "Failed building wheel for numpy/ninja"** — you don't have a C++
  compiler. Easiest fix is to use WSL (above). Otherwise install the free
  Microsoft C++ Build Tools, or `pip install numpy --only-binary :all:` first.
- **"GEMINI_API_KEY is not set"** — your `.env` isn't next to `app.py`, or still
  has the placeholder. It must sit in the same folder you run `streamlit` from.
- **Rate limit / quota errors** — Gemini 2.5 Pro has tighter free limits than
  Flash. If you hit them, open `llm.py` and set `MODEL_NAME = FAST_MODEL`.
  Caching means re-running identical inputs won't re-charge you.
- **PDF text extraction is empty** — your CV PDF is a scanned image, not real
  text. Paste the text manually, or OCR it first.
- **PDF download looks plain** — intentional. ATS parsers choke on fancy
  multi-column designs; this prioritises getting parsed correctly.
