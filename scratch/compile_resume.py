import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.append(str(BASE_DIR))

from resume_agent import compile_pdf, read_file

resume_tex_path = BASE_DIR / "resumes" / "Resume.tex"
output_pdf_path = BASE_DIR / "resumes" / "Resume.pdf"

print(f"Reading from: {resume_tex_path}")
print(f"Output to: {output_pdf_path}")

if not resume_tex_path.exists():
    print("Error: Resume.tex does not exist!")
    sys.exit(1)

tex_content = read_file(resume_tex_path)
success = compile_pdf(tex_content, resume_tex_path, output_pdf_path)

if success:
    print("PDF compiled successfully!")
else:
    print("PDF compilation failed.")
