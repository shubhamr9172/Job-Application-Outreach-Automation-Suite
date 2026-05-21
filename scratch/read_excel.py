import sys
import os

excel_path = r"d:\SR\Main Projects\Resume Details\Consultancies.xlsx"
out_path = r"d:\SR\Main Projects\Resume Details\scratch\consultancies_info.txt"

if not os.path.exists(excel_path):
    print(f"File not found: {excel_path}")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("pandas not found.\n")
    sys.exit(1)

try:
    df = pd.read_excel(excel_path)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("Columns:\n")
        f.write(str(df.columns.tolist()) + "\n\n")
        f.write("Full Excel Content:\n")
        f.write(df.to_string())
        f.write(f"\n\nTotal rows: {len(df)}\n")
    print("Excel info written successfully to text file.")
except Exception as e:
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"Error reading Excel: {e}\n")
    print(f"Error: {e}")
