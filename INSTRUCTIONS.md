# Setup & Usage Guide

Follow this guide to get the Job Application & Outreach Automation Suite up and running on your local machine.

---

## 🛠️ Step 1: Install Python & Dependencies

1. **Open your terminal / command prompt** in the project directory.
2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   ```
3. **Activate the virtual environment**:
   * **Windows (Command Prompt)**:
     ```cmd
     venv\Scripts\activate.bat
     ```
   * **Windows (PowerShell)**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   * **Mac / Linux**:
     ```bash
     source venv/bin/activate
     ```
4. **Install the required packages**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🔑 Step 2: Configure Settings (`.env`)

1. Copy `.env.example` to a new file named `.env` in the root folder:
   * **Windows (PowerShell)**:
     ```powershell
     Copy-Item .env.example .env
     ```
   * **Windows (Command Prompt)**:
     ```cmd
     copy .env.example .env
     ```
   * **Mac / Linux**:
     ```bash
     cp .env.example .env
     ```
2. Open `.env` in a text editor and fill in your details:
   - `GEMINI_API_KEY`: Get a free key from Google AI Studio.
   - `GMAIL_USER`: Your Gmail address.
   - `GMAIL_APP_PASSWORD`: Generate a 16-character **App Password** from your Google account settings (security tab under 2-Step Verification). Do *not* use your primary account password.

---

## 💻 Step 3: Run the Dashboard Server

1. Run the Python backend server:
   ```bash
   python dashboard_server.py
   ```
2. Open your web browser and go to:
   ```text
   http://localhost:8000
   ```

---

## 📄 Step 4: Parse & Setup Your Profile

1. On the web dashboard, click the **Settings** tab in the sidebar.
2. Scroll to the **Candidate Auto-fill Profile** section.
3. **Drag and drop** your resume file (PDF, TeX, TXT, or MD) into the dotted box, or click it to upload.
4. The system will extract your profile details automatically using PDF parsing and regex heuristics.
5. Review the extracted fields (Name, Email, Phone, LinkedIn, GitHub, Portfolio, current employer, and Years of Experience).
6. Fill out or correct any details, then click **Save Configuration** at the bottom.

---

## 🔌 Step 5: Install the Chrome Extension

1. Open **Google Chrome** and navigate to: `chrome://extensions/`
2. Turn on **Developer mode** (toggle in the top-right corner).
3. Click **Load unpacked** (button in the top-left corner).
4. Select the `chrome_extension` folder inside this project directory.
5. The extension icon will now appear in your browser toolbar (pin it for quick access!).

---

## ⚡ Step 6: Autofilling Job Forms

1. Go to any job application page (e.g. Lever, Greenhouse, Workable, or custom job boards).
2. Click the **Autofill Extension** icon in your toolbar.
3. Click the **⚡ Auto-fill Application Form** button.
4. The extension will automatically populate matching fields and highlight the resume upload box in a dashed **green glow** so you can easily drag and drop your resume file.

---

## 🔍 Step 7: Scrape & Discover Jobs

You can run background scrapers to find active jobs matching your settings:
* **To crawl job postings**:
  ```bash
  python job_scraper.py
  ```
  *(Matches keywords, location, and uses Gemini to filter out irrelevant postings. Finds will appear on the **Job Listings** board in the dashboard).*
  
* **To crawl recruitment agencies**:
  ```bash
  python agency_scraper.py
  ```
  *(Finds recruitment agencies in your target location. Review them under the **Discovered Agencies** tab in the dashboard).*
