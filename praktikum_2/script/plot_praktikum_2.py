#!/usr/bin/env python3
"""
Plot data for Percobaan 1 and Percobaan 3 from praktikum_2/datakita.qmd
and save PNGs into praktikum_2/media.

Usage: python3 praktikum_2/script/plot_praktikum_2.py
"""

from pathlib import Path
import re
import sys


def parse_number(text: str) -> float:
    cleaned = text.strip().replace(",", ".")
    cleaned = re.sub(r"[^0-9.+-]", "", cleaned)
    if not cleaned:
        raise ValueError("empty numeric string")
    return float(cleaned)


def slugify(text: str) -> str:
    text = text.lower()
    text = text.replace("(", "").replace(")", "")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def collect_tables(text: str):
    lines = text.splitlines()
    current_section = None
    current_title = None
    tables = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if re.search(r"Percobaan\s+1", line, re.I):
            current_section = "percobaan_1"
        elif re.search(r"Percobaan\s+3", line, re.I):
            current_section = "percobaan_3"

        title_match = re.search(r"\*\*(.+?)\*\*", line)
        if title_match and "Tegangan" in title_match.group(1):
            current_title = title_match.group(1).strip()

        if "Tegangan Input" in line and (
            "Tegangan Output" in line or "Amperemeter" in line
        ):
            header = line
            data_lines = []
            j = i + 2
            while j < len(lines):
                row = lines[j]
                if not row.strip().startswith("|"):
                    break
                if re.match(r"^\|\s*[-=]+", row):
                    j += 1
                    continue
                if "No." in row:
                    j += 1
                    continue
                data_lines.append(row)
                j += 1
            tables.append(
                {
                    "section": current_section,
                    "title": current_title,
                    "header": header,
                    "rows": data_lines,
                }
            )
            i = j
            continue

        i += 1

    return tables


def parse_xy(rows):
    x_vals = []
    y_vals = []

    for row in rows:
        cells = [c.strip() for c in row.split("|") if c.strip()]
        if len(cells) < 3:
            continue
        cells = [c.replace(">", "").strip() for c in cells]
        try:
            x_val = parse_number(cells[1])
            y_val = parse_number(cells[2])
        except Exception:
            continue
        x_vals.append(x_val)
        y_vals.append(y_val)

    return x_vals, y_vals


def plot_and_save(x_vals, y_vals, title, y_label, output_path):
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print("matplotlib is required to plot:", exc)
        raise

    plt.figure(figsize=(6, 4))
    plt.plot(x_vals, y_vals, marker="o", linestyle="-", color="C0")
    plt.xlabel("Tegangan Input (V)")
    plt.ylabel(y_label)
    plt.title(title)
    plt.grid(alpha=0.4)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()


def main():
    base_dir = Path(__file__).resolve().parents[1]
    src = base_dir / "datakita.qmd"
    out_dir = base_dir / "media"

    if not src.exists():
        print(f"Source file not found: {src}")
        sys.exit(1)

    text = src.read_text(encoding="utf-8")
    tables = collect_tables(text)

    if not tables:
        print("No matching tables found in datakita.qmd")
        sys.exit(1)

    created = []
    for table in tables:
        section = table["section"]
        if section not in {"percobaan_1", "percobaan_3"}:
            continue

        header = table["header"]
        if "Tegangan Output" in header:
            y_label = "Tegangan Output (V)"
        elif "Amperemeter" in header:
            y_label = "Arus (mA)"
        else:
            continue

        title = f"{section.replace('_', ' ').title()} - {table['title']}"
        x_vals, y_vals = parse_xy(table["rows"])
        if not x_vals:
            print(f"No data parsed for: {title}")
            continue

        file_name = f"{section}_{slugify(table['title'])}.png"
        output_path = out_dir / file_name
        plot_and_save(x_vals, y_vals, title, y_label, output_path)
        created.append(output_path)

    if not created:
        print("No plots created (no valid data parsed).")
        sys.exit(1)

    print("Created plots:")
    for path in created:
        print(f"- {path}")


if __name__ == "__main__":
    main()
