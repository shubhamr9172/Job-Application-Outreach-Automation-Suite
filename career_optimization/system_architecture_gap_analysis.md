# AI Job Hunter: System Architecture Gap Analysis

This document provides a comprehensive audit comparing your existing job outreach codebase against the 9-agent blueprint described in [job-agent-system.html](file:///d:/SR/Main%20Projects/Resume%20Details/job-agent-system.html).

---

## 📊 Summary of Agent Coverage

| Agent | Role | Status in Codebase | Existing Implementation | Gaps / Work Needed |
| :--- | :--- | :--- | :--- | :--- |
| **🧠 Orchestrator** | Master Controller & Approval Gates | **🔴 Missing** | None. Scripts are run independently by hand. | Needs a controller that handles sequence execution, context sharing, and UI prompts. |
| **01. Job Discovery** | Scout & Aggregator | **🟡 Partial** | [agency_scraper.py](file:///d:/SR/Main%20Projects/Resume%20Details/agency_scraper.py) crawls and discovers *agencies* (Google / Naukri). | Needs job board scrapers (LinkedIn, Indeed, direct career pages) to scrape specific *job listings* (JDs). |
| **02. JD Analyzer** | Intelligence Extractor | **🔴 Missing** | None. | Needs Gemini parser to extract required skills, matching score (0-100), and suitability tags. |
| **03. Resume Tailor** | Document Customizer | **🟡 Partial** | [resume_agent.py](file:///d:/SR/Main%20Projects/Resume%20Details/resume_agent.py) updates LaTeX resume based on instructions. | Needs automated prompt mapping (JD analysis requirements -> natural language LaTeX edit instructions). |
| **04. Cover Letter** | Persuasion Writer | **🔴 Missing** | None. | Needs agent to generate tailored cover letter drafts (formal, achievement, story-led variants). |
| **05. Skill Gap** | Learning Strategist | **🔴 Missing** | None. | Needs comparison engine + Google search to find relevant free courses/docs and compile study schedules. |
| **06. App Tracker** | Pipeline Manager | **🟡 Partial** | [dashboard_server.py](file:///d:/SR/Main%20Projects/Resume%20Details/dashboard_server.py) tracks agency outreach and parses Gmail inbox IMAP for replies. | Needs upgrade to support tracking of individual *job applications* (JD, role, status) in addition to agencies. |
| **07. Interview Prep** | Mock Interviewer | **🔴 Missing** | None. | Needs multi-turn interview simulator targeting the matched JD. |
| **08. Company Research** | Intel Gatherer | **🔴 Missing** | None. | Needs search integrations to find funding, Glassdoor, tech stack, and LinkedIn hiring manager info. |
| **09. Outreach** | Network Builder | **🟡 Partial** | [job_agent.py](file:///d:/SR/Main%20Projects/Resume%20Details/job_agent.py) sends cold emails to consultancies. | Needs templates and triggers to message specific hiring managers/recruiters for individual jobs. |

---

## 🔍 Detailed Analysis of Existing Core Components

### 1. Job Discovery (`Agent 01`)
* **What We Have:** A solid [agency_scraper.py](file:///d:/SR/Main%20Projects/Resume%20Details/agency_scraper.py) which crawls Google Search using venv python packages (`Scrapling`), checks and updates `discovered_agencies.json`, and extracts email addresses via deep web crawling.
* **What We Need:** Scrapers for job boards targeting actual vacancies (e.g. searching LinkedIn or Indeed for specific job JDs like "AI Engineer", "Software Engineer").

### 2. Resume Tailoring (`Agent 03`)
* **What We Have:** [resume_agent.py](file:///d:/SR/Main%20Projects/Resume%20Details/resume_agent.py) is a highly capable LaTeX parser that takes natural language updates and directly edits `Resume.tex`.
* **What We Need:** Automation so that the JD Analyzer's output is translated into structured editing prompts (e.g., "Highlight python concurrency experience and Docker in skills section") and sent to `resume_agent.py` automatically.

### 3. Application Tracking (`Agent 06`)
* **What We Have:** An excellent local dashboard ([dashboard_server.py](file:///d:/SR/Main%20Projects/Resume%20Details/dashboard_server.py) and [index.html](file:///d:/SR/Main%20Projects/Resume%20Details/dashboard_public/index.html)) which serves as the pipeline UI. It reads/writes `emailed_status.json` and parses Gmail IMAP for recruiter replies.
* **What We Need:** An extension of the storage schema and UI to support tracking specific jobs, rather than just consultancies. We should add a "Job Vacancies Tracker" tab alongside the "Agencies Tracker".

### 4. Outreach Agent (`Agent 09`)
* **What We Have:** [job_agent.py](file:///d:/SR/Main%20Projects/Resume%20Details/job_agent.py) performs bulk personalized cold emailing with resume attachments.
* **What We Need:** Sequences for job-specific outreach (e.g. cold emailing a hiring manager at a company for an active role we discovered).

---

## 🛠️ Roadmap for Future Development

Here is a recommended phasing plan if you wish to expand your workspace into the full multi-agent system:

### Phase 1: Core Job Intake & Analysis (Agents 02 & 05)
* Create `jd_analyzer.py` to parse JDs and score them.
* Create `skill_gap.py` to generate study plans for skills mismatches.

### Phase 2: Orchestrated Document Generation (Agents 03 & 04 + Orchestrator)
* Integrate `resume_agent.py` and a new `cover_letter_generator.py` into a unified pipeline.
* Create a central orchestrator controller to tie everything together.

### Phase 3: Tracking & Outreach Upgrades (Agents 06, 08 & 09)
* Upgrade `dashboard_server.py` database to support tracking specific job listings.
* Add company research (funding, tech stack) capabilities.
