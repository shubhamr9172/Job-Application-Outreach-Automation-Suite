"""Compile both Resume.tex and Resume_Support.tex to PDF via online API."""
import sys, datetime, shutil, requests
from pathlib import Path

RESUMES_DIR = Path(__file__).parent.parent / "resumes"

FILES = [
    (RESUMES_DIR / "Resume.tex",         RESUMES_DIR / "Resume.pdf"),
    (RESUMES_DIR / "Resume_Support.tex", RESUMES_DIR / "Resume_Support.pdf"),
]

# Map .tex basenames to human-friendly PDF prefixes
_PDF_NAME_MAP = {
    "Resume":         "Shubham_Reddy",
    "Resume_Support": "Shubham_Reddy_Support",
}


def get_formatted_date():
    """Return date formatted like '1st_June'."""
    now = datetime.date.today()
    day = now.day
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    month = now.strftime("%B")
    return f"{day}{suffix}_{month}"


def save_dated_pdf_copy(pdf_path):
    """Save a dated copy, e.g. Shubham_Reddy_1st_June.pdf."""
    if not pdf_path.exists():
        return None
    prefix = _PDF_NAME_MAP.get(pdf_path.stem, f"Shubham_Reddy_{pdf_path.stem}")
    date_str = get_formatted_date()
    dated_path = pdf_path.parent / f"{prefix}_{date_str}.pdf"
    shutil.copy2(pdf_path, dated_path)
    return dated_path


def compile_pdf_online(tex_content: str, output_path: Path) -> bool:
    # Attempt 1: latex.ytotech.com
    print(f"  [*] Trying latex.ytotech.com...")
    try:
        payload = {
            "compiler": "pdflatex",
            "resources": [{"main": True, "content": tex_content}],
        }
        resp = requests.post(
            "https://latex.ytotech.com/builds/sync",
            json=payload,
            timeout=120,
        )
        if resp.status_code in (200, 201) and resp.content[:5] == b"%PDF-":
            output_path.write_bytes(resp.content)
            print(f"  [OK] PDF saved: {output_path.name}")
            return True
        else:
            print(f"  [WARN] ytotech status {resp.status_code}")
    except requests.RequestException as e:
        print(f"  [WARN] ytotech error: {e}")

    # Attempt 2: texlive.net
    print(f"  [*] Trying texlive.net...")
    try:
        resp = requests.post(
            "https://texlive.net/cgi-bin/latexcgi",
            files={
                "filecontents[]": ("document.tex", tex_content.encode("utf-8"), "text/plain"),
                "filename[]": (None, "document.tex"),
                "engine": (None, "pdflatex"),
                "return": (None, "pdf"),
            },
            timeout=120,
        )
        if resp.status_code == 200 and resp.content[:5] == b"%PDF-":
            output_path.write_bytes(resp.content)
            print(f"  [OK] PDF saved: {output_path.name}")
            return True
        else:
            print(f"  [WARN] texlive.net status {resp.status_code}")
    except requests.RequestException as e:
        print(f"  [WARN] texlive.net error: {e}")

    return False


def main():
    success = 0
    for tex_path, pdf_path in FILES:
        print(f"\n{'='*50}")
        print(f"Compiling: {tex_path.name}")
        print(f"{'='*50}")
        if not tex_path.exists():
            print(f"  [ERROR] File not found: {tex_path}")
            continue
        tex_content = tex_path.read_text(encoding="utf-8")
        if compile_pdf_online(tex_content, pdf_path):
            dated = save_dated_pdf_copy(pdf_path)
            if dated:
                print(f"  [SNAPSHOT] Dated copy: {dated.name}")
            success += 1
        else:
            print(f"  [FAIL] Could not compile {tex_path.name}")

    print(f"\n{'='*50}")
    print(f"Result: {success}/{len(FILES)} PDFs compiled successfully")
    if success < len(FILES):
        print("[TIP] You can also compile at https://www.overleaf.com")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
