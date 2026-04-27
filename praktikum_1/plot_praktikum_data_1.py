#!/usr/bin/env python3
"""
Simple script to parse praktikum_data_1_hasil.qmd, plot I (mA) vs Vout (V),
and save the figure as a PNG in the same folder.

Usage: python3 praktikum_1/plot_praktikum_data_1.py
"""

from pathlib import Path
import re
import sys


def main():
    src = Path(__file__).resolve().parent / "praktikum_data_1_hasil.qmd"
    if not src.exists():
        print(f"Source file not found: {src}")
        sys.exit(1)

    text = src.read_text(encoding="utf-8")

    # Try to find the data table under the "Data asli yang dipakai" section
    start_pos = 0
    m = re.search(r"Data asli yang dipakai", text, re.I)
    if m:
        start_pos = m.end()

    header_re = re.compile(r"^\|.*Vin\s*\(V\).*I\s*\(mA\).*Vout", re.I | re.M)
    h = header_re.search(text, pos=start_pos)
    if not h:
        # fallback: search entire file
        h = header_re.search(text)
    if not h:
        print("Could not find the expected data table header in the qmd file.")
        sys.exit(1)

    # Split from header match into lines and locate header line index
    tail = text[h.start() :]
    lines = tail.splitlines()
    header_idx = None
    for idx, line in enumerate(lines):
        if header_re.match(line):
            header_idx = idx
            break
    if header_idx is None:
        print("Header index not found (unexpected).")
        sys.exit(1)

    # Data rows start after header and the separator line; gather subsequent table rows
    data_lines = []
    for line in lines[header_idx + 2 :]:
        if not line.strip():
            break
        if not line.strip().startswith("|"):
            break
        # Stop if next section/table appears
        if re.search(r"Tabel bantu|x\s*\(A\).*y\s*\(V\)", line, re.I):
            break
        # Collect only data rows (skip separator-like rows)
        if re.match(r"^\|\s*-", line):
            continue
        data_lines.append(line)

    i_vals = []  # I in mA
    vout_vals = []
    for line in data_lines:
        parts = [p.strip() for p in line.strip().split("|") if p.strip() != ""]
        if len(parts) < 5:
            continue
        try:
            i_mA = float(parts[2])
            vout = float(parts[4])
        except Exception:
            continue
        i_vals.append(i_mA)
        vout_vals.append(vout)

    if not i_vals:
        print("No data parsed from the table.")
        sys.exit(1)

    # Plot (import here so we can fail with a clear message if matplotlib missing)
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as e:
        print("Required plotting libraries are missing:", e)
        print("Install them with: python3 -m pip install matplotlib numpy")
        raise

    plt.figure(figsize=(6, 4))
    plt.plot(i_vals, vout_vals, marker="o", linestyle="-", color="C0")
    plt.xlabel("I (mA)")
    plt.ylabel("Vout (V)")
    plt.title("Vout vs I (mA) — Praktikum 1")
    plt.grid(alpha=0.5)
    out_file = Path(__file__).resolve().parent / "praktikum_data_1_plot.png"
    plt.tight_layout()
    plt.savefig(out_file, dpi=300)
    print("Saved plot to:", out_file)


if __name__ == "__main__":
    main()
