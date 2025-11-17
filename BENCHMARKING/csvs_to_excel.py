#!/usr/bin/env python3
"""
csvs_to_excel.py

Combine all CSV files in a directory into a single Excel workbook.
Each CSV becomes a sheet named after the CSV filename (sanitized).

Usage:
  python csvs_to_excel.py --input-dir "C:\path\to\csvs" --output "combined.xlsx"

Dependencies:
  pip install pandas openpyxl
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import sys

try:
	import pandas as pd
except Exception:
	print("Missing dependency: pandas. Install with: pip install pandas openpyxl")
	raise

INVALID_SHEET_CHARS = re.compile(r"[:\\\\/?*\[\]]")


def sanitize_sheet_name(name: str, used: set[str]) -> str:
	# Remove extension and invalid characters
	base = Path(name).stem
	base = INVALID_SHEET_CHARS.sub("_", base).strip()
	if not base:
		base = "sheet"
	# Excel sheet name limit
	max_len = 31
	if len(base) > max_len:
		base = base[:max_len]
	orig = base
	i = 1
	while base in used:
		suffix = f"_{i}"
		allowed = max_len - len(suffix)
		base = (orig[:allowed] if len(orig) > allowed else orig) + suffix
		i += 1
	used.add(base)
	return base


def find_csvs(directory: Path, pattern: str = "*.csv") -> list[Path]:
	return sorted(directory.glob(pattern))


def main() -> None:
	p = argparse.ArgumentParser(description="Combine CSVs into one Excel workbook (one sheet per CSV).")
	p.add_argument("--input-dir", "-i", required=True, help="Directory containing CSV files")
	p.add_argument("--output", "-o", required=True, help="Output Excel file path")
	p.add_argument("--pattern", "-p", default="*.csv", help="Glob pattern to match CSV files")
	p.add_argument("--engine", choices=("openpyxl", "xlsxwriter"), default="openpyxl", help="Excel writer engine")
	args = p.parse_args()

	input_dir = Path(args.input_dir).expanduser().resolve()
	if not input_dir.exists() or not input_dir.is_dir():
		print(f"Input directory not found: {input_dir}")
		sys.exit(1)

	out_path = Path(args.output).expanduser().resolve()
	csv_files = find_csvs(input_dir, args.pattern)
	if not csv_files:
		print(f"No CSV files found in {input_dir} matching pattern {args.pattern}")
		sys.exit(1)

	print(f"Found {len(csv_files)} CSV(s). Writing to {out_path}")

	used_names: set[str] = set()
	with pd.ExcelWriter(out_path, engine=args.engine) as writer:
		for csv in csv_files:
			print(f"Reading: {csv.name}")
			try:
				df = pd.read_csv(csv)
			except Exception as e:
				print(f"  Skipping {csv.name}: failed to read CSV ({e})")
				continue
			sheet = sanitize_sheet_name(csv.name, used_names)
			try:
				df.to_excel(writer, sheet_name=sheet, index=False)
				print(f"  Wrote sheet: {sheet} (rows: {len(df)})")
			except Exception as e:
				print(f"  Failed to write sheet for {csv.name}: {e}")

	print("Done.")
	print(f"Output: {out_path}")


if __name__ == "__main__":
	main()
