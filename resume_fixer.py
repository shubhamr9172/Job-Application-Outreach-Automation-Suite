"""
Resume Fixer Agent
-------------------
Consumes findings from data/resume_audit_results.json, updates the
LaTeX resume source, and compiles the final result to PDF.

Usage:
    python resume_fixer.py
    python resume_fixer.py --diff-only
"""

import sys
import json
import os
import argparse
import time
from pathlib import Path
from dotenv import load_dotenv

# Force UTF-8 encoding on Windows to prevent output print crashes
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# --- Constants & Paths --------------------------------------------------------
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
ENV_FILE = BASE_DIR / ".env"
AUDIT_RESULTS_FILE = DATA_DIR / "resume_audit_results.json"

# Import helper functions directly from resume_agent
try:
    sys.path.append(str(BASE_DIR))
    from resume_agent import (
        compile_pdf,
        generate_diff,
        extract_latex,
        validate_latex,
        backup_resume,
        load_api_key,
        read_file,
        compute_hash
    )
except ImportError as e:
    print(f"[ERROR] Failed to import from resume_agent.py: {e}")
    sys.exit(1)

load_dotenv(ENV_FILE)

# --- Fixer Logic --------------------------------------------------------------
SYSTEM_PROMPT = """You are an expert LaTeX resume editor. Your job is to take the user's current LaTeX resume source and apply the recommended corrections from the resume audit report precisely.

RULES:
1. Return ONLY the complete, updated LaTeX source code inside a ```latex code block.
2. Do NOT add any explanation, commentary, or markdown outside the code block.
3. Preserve ALL existing content, formatting, comments, and structure unless the audit report explicitly asks you to change or remove something.
4. Maintain consistent LaTeX formatting style (indentation, spacing, comments).
5. All claims must be believable -- no fabricated metrics.
6. The Copilot Studio agent is ALWAYS no-code. Never imply Python/Gemini for it.
7. Experience started May 2024. Calculate duration accurately.
8. Ensure every \\begin{} has a matching \\end{}.
9. Apply the fixes to resolve the issues described in the audit findings. Do NOT make unrequested changes.
"""

def apply_fixes(api_key: str, current_latex: str, audit_data: dict) -> str:
    """Send resume + audit findings to Gemini and get updated LaTeX source."""
    from google import genai
    client = genai.Client(api_key=api_key)

    findings_summary = []
    for idx, finding in enumerate(audit_data.get("findings", []), 1):
        findings_summary.append(
            f"Finding {idx} [{finding.get('severity').upper()}] @ {finding.get('location')}:\n"
            f"  - Issue: {finding.get('description')}\n"
            f"  - Recommendation: {finding.get('recommended_correction')}"
        )
    findings_str = "\n\n".join(findings_summary)

    prompt = f"""Here is my current LaTeX resume:

```latex
{current_latex}
```

Please fix the following issues identified in the audit report:
{findings_str}

Return the COMPLETE updated LaTeX source inside a ```latex code block. Do not omit any unchanged sections.
"""

    print("[*] Contacting Gemini to apply fixes...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,
        ),
    )
    return response.text

def main():
    parser = argparse.ArgumentParser(description="Fix LaTeX resume based on auditor findings.")
    parser.add_argument("--diff-only", action="store_true",
                        help="Show the diff of fixes without writing or compiling")
    parser.add_argument("--no-pdf", action="store_true",
                        help="Skip compiling the updated resume to PDF")
    parser.add_argument("--no-backup", action="store_true",
                        help="Skip creating a backup before saving changes")
    
    args = parser.parse_args()

    # -- Check Audit Findings --
    if not AUDIT_RESULTS_FILE.exists():
        print(f"[ERROR] Audit results file not found at: {AUDIT_RESULTS_FILE}")
        print("  Please run resume_auditor.py first to generate findings.")
        sys.exit(1)

    try:
        audit_data = json.loads(AUDIT_RESULTS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] Failed to read audit results file: {e}")
        sys.exit(1)

    findings = audit_data.get("findings", [])
    if not findings:
        print("[INFO] No findings or mistakes were recorded in the audit results. Nothing to fix.")
        sys.exit(0)

    # -- Load Config and Resume --
    config_file = DATA_DIR / "user_config.json"
    resume_path = BASE_DIR / "resumes" / "Resume.tex"
    output_pdf_path = BASE_DIR / "resumes" / "Resume.pdf"
    backup_dir = BASE_DIR / "resumes" / "backups"

    if config_file.exists():
        try:
            config = json.loads(config_file.read_text(encoding="utf-8"))
            if "resume_file_path" in config:
                resume_path = BASE_DIR / config["resume_file_path"]
                output_pdf_path = resume_path.with_suffix(".pdf")
            if "backup_dir_path" in config:
                backup_dir = BASE_DIR / config["backup_dir_path"]
        except Exception as e:
            print(f"[WARN] Error loading user_config.json: {e}. Using defaults.")

    if not resume_path.exists():
        print(f"[ERROR] Resume file not found at: {resume_path}")
        sys.exit(1)

    current_latex = read_file(resume_path)
    current_hash = compute_hash(current_latex)

    print("=" * 60)
    print("  RESUME FIXER AGENT")
    print("=" * 60)
    print(f"Applying fixes to: {resume_path.name}")
    print(f"Loaded {len(findings)} findings from {AUDIT_RESULTS_FILE.name}")

    # -- Call Gemini to Fix --
    api_key = load_api_key()
    start_time = time.time()
    try:
        response = apply_fixes(api_key, current_latex, audit_data)
    except Exception as e:
        print(f"[ERROR] Gemini API error: {e}")
        sys.exit(1)

    print(f"[AI] Response received in {time.time() - start_time:.1f}s")

    # -- Process Response --
    updated_latex = extract_latex(response)
    new_hash = compute_hash(updated_latex)

    if current_hash == new_hash:
        print("\n[WARN] No changes detected. The fixer agent did not modify the LaTeX code.")
        sys.exit(0)

    # Validate output
    issues = validate_latex(updated_latex)
    if issues:
        print("\n[WARN] LaTeX Validation Warnings:")
        for issue in issues:
            print(f"  - {issue}")
        if any("Missing" in i for i in issues):
            print("\n[ERROR] Critical validation failures detected in the generated LaTeX. Aborting.")
            sys.exit(1)

    # Generate and show diff
    diff = generate_diff(current_latex, updated_latex)
    print("\n" + "-" * 60)
    print("PROPOSED FIXES (DIFF):")
    print("-" * 60)
    print(diff)
    print("-" * 60)

    if args.diff_only:
        print("\n[INFO] Diff-only mode -- no files were modified.")
        sys.exit(0)

    # -- User Confirmation --
    try:
        confirm = input("\nApply these fixes and update your resume? [Y/n]: ").strip().lower()
    except EOFError:
        confirm = "y"
    
    if confirm not in ("", "y", "yes"):
        print("[CANCELLED]")
        sys.exit(0)

    # -- Backup & Save --
    if not args.no_backup:
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{resume_path.stem}_{ts}.tex"
        import shutil
        shutil.copy2(resume_path, backup_path)
        print(f"[BACKUP] Saved to {backup_path.name}")

    resume_path.write_text(updated_latex, encoding="utf-8")
    print(f"[UPDATED] {resume_path.name}")

    # -- Compile PDF --
    if not args.no_pdf:
        pdf_ok = compile_pdf(updated_latex, resume_path, output_pdf_path)
        if pdf_ok:
            print(f"[SUCCESS] Resume updated and compiled to {output_pdf_path}")
        else:
            print("[WARN] PDF compilation failed. LaTeX file was saved, but PDF could not be generated.")
    else:
        print("[SKIP] PDF compilation skipped (--no-pdf)")

if __name__ == "__main__":
    main()
