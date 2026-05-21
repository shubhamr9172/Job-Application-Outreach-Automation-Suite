# Job Application & Outreach Automation Suite

An automated, end-to-end suite designed to streamline job discovery, tracking, candidate profiling, and application auto-filling. It features a local glassmorphic Web Dashboard, Google Gemini AI-driven scraper agents, automated Gmail response tracking, and a powerful Chrome Extension to autofill applications on popular portals.

---

## ⚡ Key Features

1. **Local Web Dashboard (`http://localhost:8000`)**
   - **Outreach Tracker**: Tracks recruitment consultancies from `Consultancies.xlsx` merged with `emailed_status.json`.
   - **Gmail Replies Integration**: Syncs and displays replies from Gmail using IMAP with an App Password.
   - **Discovered Agencies**: Review, approve, or reject new recruiting agencies found by the web search crawler.
   - **Job Listings Board**: View scraped job postings, track details, and approve jobs with the "Approve & Track" workflow.
   - **Interactive Settings & Resume Uploader**: Configures job preferences, file paths, and candidate details. Includes a drag-and-drop resume parser supporting PDF, TXT, TeX, and MD formats.

2. **Resume Parser Backend**
   - Integrates `pypdf` to parse and extract text from binary PDF resumes.
   - Applies matching regex heuristics to automatically extract and populate candidate details (Name, Contact info, Social/GitHub links, Current Company, and Years of Experience) directly into the settings.

3. **Chrome Extension Auto-filler**
   - **Intelligent Autofill**: Auto-populates complex application fields (emails, phone numbers, GitHub/LinkedIn links, current employer, portfolio, and work experience) using smart label matching.
   - **React/Vue Compatibility**: Dispatches appropriate framework events (`input` / `change`) to trigger site validation states.
   - **Visual Cue Dropzones**: Automatically highlights resume upload zones in green dashed borders for easy drag-and-drop.

4. **Stealth Scrapers & AI Agents**
   - **Stealth Job Scraper**: Crawls portals and search engines using a stealth-enabled crawler (`scrapling`) to find potential jobs.
   - **AI Job/Agency Filtering**: Filters and structures scraped listings using Google Gemini AI (`google-genai`).

---

## 🛠️ Tech Stack

### Backend Services
* **Core Language**: Python 3.10+
* **HTTP Server**: Built-in `http.server` (custom lightweight router with multipart-form parsing)
* **Excel Processing**: `pandas` & `openpyxl`
* **PDF Extraction**: `pypdf`
* **Web Crawling**: `scrapling` (stealthy fetching engine)
* **AI Model Engine**: Google Gemini API via `google-genai` SDK
* **Secrets Management**: `python-dotenv`

### Frontend Dashboard
* **Structure & UI**: Vanilla HTML5, semantic markup
* **Styling**: Vanilla CSS3 (Custom Glassmorphic Dark UI, modern typography, grid/flex layouts, transition effects)
* **Logic**: Vanilla JavaScript (ES6+ async fetch API, drag-and-drop handlers, interactive toasts)

### Chrome Extension
* **Standard**: Chrome Extension Manifest V3
* **Scripts**: Background service workers & Content injection scripts (`content.js`, `popup.js`)
* **Styling**: Vanilla CSS variables, responsive design

---

## 📂 Project Directory Structure

```text
├── chrome_extension/        # Chrome Extension source code
│   ├── manifest.json        # Extension configuration file
│   ├── content.js           # Content script for autofilling forms
│   ├── popup.html           # Popup window markup
│   ├── popup.js             # Extension interaction controller
│   └── popup.css            # Extension visual styles
│
├── dashboard_public/        # Static frontend assets
│   └── index.html           # Core dashboard interface file
│
├── data/                    # JSON data storage
│   ├── user_config.json     # Saved app configurations and profile
│   ├── emailed_status.json  # Consultancies outreach history
│   ├── jobs.json            # Scraped job postings
│   └── discovered_agencies.json # Candidate agencies waiting for approval
│
├── docs/                    # Context files & project architecture docs
├── agency_scraper.py        # IT/AI recruitment agency discovery script
├── job_scraper.py           # Stealth job crawler using Scrapling & Gemini
├── job_agent.py             # Agent script for job validation
├── resume_agent.py          # Agent script for resume customisations
├── dashboard_server.py      # Core Python web backend server
├── Consultancies.xlsx       # List of target consultancies
├── requirements.txt         # Python library dependencies list
└── .env                     # Local secrets configuration (ignored by git)
```

---

## 📝 Configuration File (`.env`)

Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

For step-by-step setup, running instructions, and how to use the dashboard and extension, please refer to [INSTRUCTIONS.md](file:///d:/SR/Main%20Projects/Resume%20Details/INSTRUCTIONS.md).
