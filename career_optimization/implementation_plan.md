# Implementation Plan: Job Outreach Suite - Multi-Agent System Gaps

We will implement a complete, modular, multi-agent pipeline and integrate it directly into the existing local Python dashboard. This will bridge the gaps identified in the [System Architecture Gap Analysis](system_architecture_gap_analysis.md) by introducing intelligent job analysis, document tailoring, learning plans, mock interviews, and dashboard UI upgrades.

---

## User Review Required

> [!IMPORTANT]
> **Key Design and Architectural Decisions**
> 1. **Data-Centric JSON Storage Upgrade**: We will augment `data/jobs_tracker.json` to store new fields: `suitability_score` (int), `matching_skills` (list), `missing_skills` (list), `resume_suggestions` (list), `cover_letter` (text), `study_plan` (text), `company_intel` (text), and `interview_chat_history` (list).
> 2. **Stealthy Scraper Reuse**: The analyzer will reuse the existing HTTP search/fetcher tools or accept raw text pasted from the UI to bypass cloudflare blocks on major job portals.
> 3. **Draft-First Document Workflows**: Resume changes and cover letter generations are saved as local drafts first. The user can review, edit, copy, or trigger compile commands through the dashboard before anything is finalized.

---

## Open Questions

> [!WARNING]
> **Decisions Needed from the User**
> * **LaTeX Compilation**: When updating the resume with `resume_agent.py`, do you have a local LaTeX compiler (`pdflatex` or `xelatex`) installed, or do you prefer to compile manually using Overleaf or an external tool? We will configure the orchestrator to compile automatically if the compiler is detected, otherwise fallback to saving the `.tex` file.
> * **Gemini API Model Choice**: We default to using `gemini-2.5-flash` for high-speed analysis and low latency. If you require deep logical reasoning for cover letter writing, we can optionally route those specific calls to `gemini-2.5-pro` (if enabled on your API key).

---

## Proposed Changes

We will implement the solution in three logical phases.

### Phase 1: Modular Agent Foundation (Agents 02, 04, 05)

We will build the core Python agents responsible for analyzing job postings, writing documents, and mapping learning roadmaps.

#### [NEW] [jd_analyzer.py](jd_analyzer.py)
* Creates a parser class using the Google `genai` SDK (`gemini-2.5-flash`).
* Accepts raw job description text.
* Evaluates the JD against the baseline `Resume.tex` and `# Shubham — Career Context File.md`.
* Outputs structured JSON conforming to a Pydantic schema:
  * `suitability_score`: Match percentage (0-100).
  * `matching_skills`: List of skills Shubham has that are relevant.
  * `missing_skills`: List of skills requested but missing.
  * `resume_suggestions`: List of concrete editing suggestions for the LaTeX resume.
  * `key_role_details`: Role seniority, core tech stack, and division.

#### [NEW] [cover_letter_generator.py](cover_letter_generator.py)
* Generates a tailored cover letter (around 250-300 words) using Gemini.
* Matches the writing tone to the company culture and details from the JD.
* Highlights Shubham's achievements matching the specific role requirements.

#### [NEW] [skill_gap_agent.py](skill_gap_agent.py)
* Takes the list of `missing_skills` from `jd_analyzer.py`.
* Compiles a custom study plan with week-by-week learning goals.
* Recommends free online learning resources, documentation guides, and tutorials.

---

### Phase 2: Master Orchestrator & CLI Tooling

We will link all agents together and create a clean command-line entry point.

#### [NEW] [orchestrator.py](orchestrator.py)
* Coordinates the multi-agent execution pipeline.
* Given a job link and description:
  1. Executes `jd_analyzer.py` to extract match statistics.
  2. Executes `cover_letter_generator.py` to draft the letter.
  3. Executes `skill_gap_agent.py` to create the learning roadmap.
  4. Saves all results back to the database in `jobs_tracker.json`.
* Exposes CLI commands to run individual steps or trigger resume updates via `resume_agent.py`.

---

### Phase 3: Dashboard Integration & Premium UI (Agents 06 & 07)

We will modify the dashboard backend to serve these agents and upgrade the web interface to display results elegantly.

#### [MODIFY] [dashboard_server.py](dashboard_server.py)
* Add `/api/jobs/analyze` endpoint (POST): Triggers the orchestrator pipeline for a specific job entry.
* Add `/api/jobs/save-cl` endpoint (POST): Allows saving manual edits made to the cover letter draft.
* Add `/api/jobs/mock-interview` endpoint (POST): Handles multi-turn chat sessions simulating an interview for the target job.
* Update `/api/jobs/status` and updates database logging to handle the new structured metadata fields.

#### [MODIFY] [index.html](dashboard_public/index.html)
* **Upgrade Tracked Job Cards**: Add match score badges (e.g. `85% Match` with green/yellow/red color-coding) and an "AI Action Center" button.
* **Interactive AI Optimization Modal**: Build a sleek, responsive, slide-out modal or popup containing:
  * **Score & Skills Overview**: Displays matching skills, missing skills, and resume recommendations.
  * **Cover Letter Editor**: View and live-edit the generated cover letter with a "Copy to Clipboard" button.
  * **Study Guide**: Interactive checkbox checklist of the week-by-week study guide.
  * **Mock Interview Simulator**: Chat interface to practice questions with live AI feedback.
* **Micro-animations & CSS Styles**: Include modern styling (glassmorphism tabs, pulse loading state, smooth height transitions) to make the UI look and feel premium.

---

## Verification Plan

### Automated Tests
* Run a verification suite checking schema consistency:
  ```powershell
  python -c "import json; d=json.load(open('data/jobs_tracker.json', encoding='utf-8')); assert isinstance(d, list); print('Jobs tracker JSON structure verified successfully.')"
  ```
* Run `jd_analyzer.py` on a sample JD to assert that all schema keys (`suitability_score`, `matching_skills`, `missing_skills`, etc.) are returned correctly.

### Manual Verification
1. Start the server via `python dashboard_server.py`.
2. Open the dashboard in the browser.
3. Click "AI Action Center" on a job listing card.
4. Trigger "Run AI Optimization" and verify the loading indicator, match score rendering, cover letter draft extraction, and learning plan compilation.
5. Compile the modified LaTeX file to ensure no syntax errors are introduced.
