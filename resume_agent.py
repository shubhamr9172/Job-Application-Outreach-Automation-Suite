"""
Resume Update Agent
-------------------
A CLI agent that takes natural-language resume update instructions,
modifies your LaTeX resume, and compiles it to PDF.

Usage:
    python resume_agent.py                           # interactive mode
    python resume_agent.py "Add Docker to core skills"  # one-shot mode
    python resume_agent.py --diff-only "..."         # preview changes without writing

Requirements:
    pip install google-genai python-dotenv requests
    Create a .env file with: GEMINI_API_KEY=your_key_here
"""

import sys
import json
import os
import io
import re
import argparse
import shutil
import datetime
import hashlib
import textwrap
import time
import difflib
import requests
from pathlib import Path

from dotenv import load_dotenv
from google import genai

# Force UTF-8 stdout/stderr on Windows to avoid cp1252 encoding crashes
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# --- Config -------------------------------------------------------------------
RESUME_DIR  = Path(__file__).parent.resolve()
DATA_DIR    = RESUME_DIR / "data"
CONFIG_FILE = DATA_DIR / "user_config.json"

# Default fallback paths (now in resumes/ subfolder)
RESUME_TEX  = RESUME_DIR / "resumes" / "Resume.tex"
CONTEXT_MD  = RESUME_DIR / "resumes" / "career_context.md"
BACKUP_DIR  = RESUME_DIR / "resumes" / "backups"
OUTPUT_PDF  = RESUME_DIR / "resumes" / "Resume.pdf"

# Load customized paths from config if present
if CONFIG_FILE.exists():
    try:
        config_data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if "resume_file_path" in config_data:
            RESUME_TEX = RESUME_DIR / config_data["resume_file_path"]
            OUTPUT_PDF = RESUME_TEX.with_suffix(".pdf")
        if "context_file_path" in config_data:
            CONTEXT_MD = RESUME_DIR / config_data["context_file_path"]
        if "backup_dir_path" in config_data:
            BACKUP_DIR = RESUME_DIR / config_data["backup_dir_path"]
    except Exception as e:
        print(f"[WARN] Failed to load config path: {e}")

GEMINI_MODEL     = "gemini-2.5-flash"

# --- Helpers ------------------------------------------------------------------

def load_api_key() -> str:
    """Load Gemini API key from .env or environment."""
    load_dotenv(RESUME_DIR / ".env")
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("[ERROR] GEMINI_API_KEY not found.")
        print(f"  Create {RESUME_DIR / '.env'} with:\n  GEMINI_API_KEY=your_key_here")
        sys.exit(1)
    return key


def read_file(path: Path) -> str:
    """Read a text file with UTF-8 encoding."""
    return path.read_text(encoding="utf-8")


def backup_resume() -> Path:
    """Create a timestamped backup of Resume.tex before modifying."""
    BACKUP_DIR.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = RESUME_TEX.stem
    backup_path = BACKUP_DIR / f"{base_name}_{ts}.tex"
    shutil.copy2(RESUME_TEX, backup_path)
    return backup_path


# Map .tex basenames to human-friendly PDF prefixes
_PDF_NAME_MAP = {
    "Resume":         "Shubham_Reddy",
    "Resume_Support": "Shubham_Reddy_Support",
}


def get_formatted_date() -> str:
    """Return date formatted like '1st_June'."""
    now = datetime.date.today()
    day = now.day
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    month = now.strftime("%B")
    return f"{day}{suffix}_{month}"


def save_dated_pdf_copy(pdf_path: Path) -> Path | None:
    """Save a dated copy of the compiled PDF, e.g. Shubham_Reddy_1st_June.pdf.

    The copy is placed in the same directory as the original PDF.
    Only one copy per (track, date) is kept — a later compile on the
    same day overwrites the earlier snapshot.
    """
    if not pdf_path.exists():
        return None

    tex_stem = pdf_path.stem  # e.g. "Resume" or "Resume_Support"
    prefix = _PDF_NAME_MAP.get(tex_stem, f"Shubham_Reddy_{tex_stem}")
    date_str = get_formatted_date()
    dated_name = f"{prefix}_{date_str}.pdf"
    dated_path = pdf_path.parent / dated_name

    shutil.copy2(pdf_path, dated_path)
    return dated_path


def compute_hash(content: str) -> str:
    """SHA-256 hash of a string to detect changes."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def generate_diff(old: str, new: str) -> str:
    """Generate a unified-diff-style comparison."""
    old_lines = old.splitlines()
    new_lines = new.splitlines()

    diff_lines = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile="Resume.tex (before)",
        tofile="Resume.tex (after)",
        lineterm=""
    ))

    return "\n".join(diff_lines) if diff_lines else "(no changes detected)"


def extract_latex(response_text: str) -> str:
    """Extract LaTeX code from the Gemini response.

    Handles three formats:
      1. Fenced code block: ```latex ... ```  or  ``` ... ```
      2. Raw LaTeX starting with \\documentclass
      3. Entire response as LaTeX
    """
    # Try fenced code block first
    pattern = r"```(?:latex|tex)?\s*\n(.*?)```"
    match = re.search(pattern, response_text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try to find raw LaTeX
    idx = response_text.find("\\documentclass")
    if idx != -1:
        end_idx = response_text.rfind("\\end{document}")
        if end_idx != -1:
            return response_text[idx:end_idx + len("\\end{document}")].strip()
        return response_text[idx:].strip()

    # Fallback: return as-is
    return response_text.strip()


def validate_latex(latex: str) -> list[str]:
    """Basic validation checks on the LaTeX output."""
    issues = []
    if "\\documentclass" not in latex:
        issues.append("Missing \\documentclass")
    if "\\begin{document}" not in latex:
        issues.append("Missing \\begin{document}")
    if "\\end{document}" not in latex:
        issues.append("Missing \\end{document}")

    # Check balanced braces (rough)
    open_count = latex.count("{")
    close_count = latex.count("}")
    if abs(open_count - close_count) > 2:
        issues.append(f"Unbalanced braces: open={open_count}, close={close_count}")

    # Check key info is preserved
    if "Shubham Reddy" not in latex:
        issues.append("Name 'Shubham Reddy' missing -- possible data loss")
    if "Tata Consultancy" not in latex:
        issues.append("TCS experience missing -- possible data loss")

    return issues


def compile_pdf_online(tex_content: str, output_path: Path) -> bool:
    """Compile LaTeX to PDF using online APIs.

    Tries multiple services in order:
      1. latex.ytotech.com (free community API - reliable)
      2. texlive.net (TeX Live backend, multipart upload)
    """
    # --- Attempt 1: latex.ytotech.com ---
    print("[*] Compiling PDF via latex.ytotech.com...")
    try:
        payload = {
            "compiler": "pdflatex",
            "resources": [
                {
                    "main": True,
                    "content": tex_content,
                }
            ],
        }
        resp = requests.post(
            "https://latex.ytotech.com/builds/sync",
            json=payload,
            timeout=90,
        )
        if resp.status_code in (200, 201) and resp.content[:5] == b"%PDF-":
            output_path.write_bytes(resp.content)
            print(f"[OK] PDF saved: {output_path}")
            return True
        else:
            print(f"[WARN] ytotech returned status {resp.status_code}")
    except requests.RequestException as e:
        print(f"[WARN] ytotech error: {e}")

    # --- Attempt 2: texlive.net ---
    print("[*] Trying texlive.net...")
    try:
        resp = requests.post(
            "https://texlive.net/cgi-bin/latexcgi",
            files={
                "filecontents[]": ("document.tex", tex_content.encode("utf-8"), "text/plain"),
                "filename[]": (None, "document.tex"),
                "engine": (None, "pdflatex"),
                "return": (None, "pdf"),
            },
            timeout=90,
        )
        if resp.status_code == 200 and resp.content[:5] == b"%PDF-":
            output_path.write_bytes(resp.content)
            print(f"[OK] PDF saved: {output_path}")
            return True
        else:
            print(f"[WARN] texlive.net returned status {resp.status_code}")
    except requests.RequestException as e:
        print(f"[WARN] texlive.net error: {e}")

    return False


def compile_pdf_local(tex_path: Path) -> bool:
    """Try compiling with local pdflatex if available."""
    import subprocess
    pdflatex = shutil.which("pdflatex")
    if not pdflatex:
        return False

    print("[*] Compiling PDF with local pdflatex...")
    result = subprocess.run(
        [pdflatex, "-interaction=nonstopmode", "-output-directory", str(tex_path.parent), str(tex_path)],
        capture_output=True, text=True, cwd=str(tex_path.parent)
    )
    if result.returncode == 0:
        print("[OK] PDF compiled successfully")
        return True
    else:
        print(f"[WARN] pdflatex failed:\n{result.stderr[:500]}")
        return False


def compile_pdf(tex_content: str, tex_path: Path, output_path: Path) -> bool:
    """Compile LaTeX -> PDF. Tries local pdflatex first, then online API."""
    if compile_pdf_local(tex_path):
        return True
    return compile_pdf_online(tex_content, output_path)


# --- Core Agent ---------------------------------------------------------------

SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert LaTeX resume editor. Your job is to take the user's
    current LaTeX resume source and apply their requested changes precisely.

    RULES:
    1. Return ONLY the complete, updated LaTeX source code inside a ```latex code block.
    2. Do NOT add any explanation, commentary, or markdown outside the code block.
    3. Preserve ALL existing content, formatting, comments, and structure unless
       the user explicitly asks you to change or remove something.
    4. Maintain consistent LaTeX formatting style (indentation, spacing, comments).
    5. Keep the same document class, packages, and preamble unless changes require new packages.
    6. All claims must be believable -- no fabricated metrics.
    7. The Copilot Studio agent is ALWAYS no-code. Never imply Python/Gemini for it.
    8. Experience started May 2024. Calculate duration accurately.
    9. When adding items, place them in the most logical section.
    10. When adding skills, check if they already exist to avoid duplicates.
    11. Use standard LaTeX escaping: %, $, &, #, _ must be backslash-escaped in text.
    12. Ensure every \\begin{} has a matching \\end{}.

    CONTEXT about the person (use for accuracy, not for adding unrequested content):
    - Name: Shubham Reddy
    - Role: System Engineer at TCS, Pune
    - Target: AI Engineer / Gen AI Developer
    - Core stack: LangGraph, LangChain, RAG, Gemini API, Python
""")


def call_gemini(api_key: str, current_latex: str, instructions: str) -> str:
    """Send the resume + update instructions to Gemini and get updated LaTeX."""
    client = genai.Client(api_key=api_key)

    prompt = f"""Here is my current LaTeX resume:

```latex
{current_latex}
```

Apply the following changes:
{instructions}

Return the COMPLETE updated LaTeX source inside a ```latex code block.
Do not omit any sections. Return the full document."""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,
        ),
    )
    return response.text


# --- CLI ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Resume Update Agent -- update your LaTeX resume with natural language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python resume_agent.py "Add Kubernetes to supporting skills"
              python resume_agent.py "Update summary to mention 2.5 years of experience"
              python resume_agent.py --diff-only "Remove the Additional section"
              python resume_agent.py --no-pdf "Fix the LangSmith duplicate in skills"
              python resume_agent.py                          # interactive mode
        """)
    )
    parser.add_argument("instructions", nargs="?", default=None,
                        help="Update instructions in natural language")
    parser.add_argument("--diff-only", action="store_true",
                        help="Show the diff without writing changes")
    parser.add_argument("--no-pdf", action="store_true",
                        help="Update .tex file but skip PDF compilation")
    parser.add_argument("--no-backup", action="store_true",
                        help="Skip creating a backup before writing")

    args = parser.parse_args()

    # -- Banner --
    print("=" * 50)
    print("  RESUME UPDATE AGENT -- Shubham Reddy")
    print("=" * 50)
    print()

    # -- Get instructions --
    instructions = args.instructions
    if not instructions:
        print("Enter your resume update instructions")
        print("(press Enter twice to submit):\n")
        lines = []
        while True:
            try:
                line = input()
                if line == "" and lines and lines[-1] == "":
                    break
                lines.append(line)
            except EOFError:
                break
        instructions = "\n".join(lines).strip()

    if not instructions:
        print("[ERROR] No instructions provided. Exiting.")
        sys.exit(1)

    preview = instructions[:120] + ("..." if len(instructions) > 120 else "")
    print(f"\n[INSTRUCTIONS] {preview}")

    # -- Load resume --
    if not RESUME_TEX.exists():
        print(f"[ERROR] Resume file not found: {RESUME_TEX}")
        sys.exit(1)

    current_latex = read_file(RESUME_TEX)
    current_hash = compute_hash(current_latex)
    print(f"[LOADED] {RESUME_TEX.name} ({len(current_latex)} chars)")

    # -- Call Gemini --
    api_key = load_api_key()
    print(f"[AI] Calling {GEMINI_MODEL}...")
    start = time.time()

    try:
        response = call_gemini(api_key, current_latex, instructions)
    except Exception as e:
        print(f"[ERROR] Gemini API error: {e}")
        sys.exit(1)

    elapsed = time.time() - start
    print(f"[AI] Response received in {elapsed:.1f}s")

    # -- Extract & validate --
    updated_latex = extract_latex(response)
    new_hash = compute_hash(updated_latex)

    if current_hash == new_hash:
        print("\n[WARN] No changes detected -- the resume appears unchanged.")
        sys.exit(0)

    issues = validate_latex(updated_latex)
    if issues:
        print("\n[WARN] Validation warnings:")
        for issue in issues:
            print(f"  - {issue}")
        if any("Missing" in i for i in issues):
            print("\n[ERROR] Critical validation failure -- aborting to protect your resume.")
            sys.exit(1)

    # -- Show diff --
    diff = generate_diff(current_latex, updated_latex)
    print("\n" + "-" * 50)
    print("CHANGES:")
    print("-" * 50)
    print(diff)
    print("-" * 50)

    if args.diff_only:
        print("\n[INFO] Diff-only mode -- no files were modified.")
        sys.exit(0)

    # -- Confirm --
    try:
        confirm = input("\nApply these changes? [Y/n]: ").strip().lower()
    except EOFError:
        confirm = "y"
    if confirm not in ("", "y", "yes"):
        print("[CANCELLED]")
        sys.exit(0)

    # -- Backup --
    if not args.no_backup:
        backup_path = backup_resume()
        print(f"[BACKUP] Saved: {backup_path.name}")

    # -- Write updated .tex --
    RESUME_TEX.write_text(updated_latex, encoding="utf-8")
    print(f"[UPDATED] {RESUME_TEX.name}")

    # -- Compile PDF --
    if not args.no_pdf:
        pdf_ok = compile_pdf(updated_latex, RESUME_TEX, OUTPUT_PDF)
        if pdf_ok:
            dated = save_dated_pdf_copy(OUTPUT_PDF)
            if dated:
                print(f"[SNAPSHOT] Dated copy saved: {dated.name}")
        else:
            print("\n[TIP] You can compile manually at https://www.overleaf.com")
            print("  or install MiKTeX/TeXLive for local compilation.")
    else:
        print("[SKIP] PDF compilation skipped (--no-pdf)")

    # -- Done --
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n[DONE] Resume updated successfully at {ts}")
    print(f"  .tex -> {RESUME_TEX}")
    if not args.no_pdf and OUTPUT_PDF.exists():
        print(f"  .pdf -> {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
