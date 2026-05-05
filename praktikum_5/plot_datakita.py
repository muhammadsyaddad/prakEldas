#!/usr/bin/env python3
"""
plot_datakita.py

Read praktikum_5/datakita.qmd and plot available data tables using matplotlib.

By default this script searches the markdown tables in the input file and:
- for tables that contain both "Arus" and "V dioda" columns it plots Arus (mA)
  on the x-axis and V dioda (V) on the y-axis;
- for tables that contain "Volt" (input) and "Vrms" columns it produces
  Volt Input vs Vrms (for diode and resistor) plots.

Usage examples:
  python praktikum_5/plot_datakita.py
  python praktikum_5/plot_datakita.py --input praktikum_5/datakita.qmd --outdir plots --no-show

The script only requires matplotlib (and Python 3.7+).
"""

from __future__ import annotations

import argparse
import os
import re
from typing import List, Optional, Tuple

import matplotlib.pyplot as plt


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def find_tables(text: str) -> List[dict]:
    """Find markdown tables in the text.

    Returns a list of dict with keys: heading, lines (list of table lines)
    Heading is the nearest preceding heading-like line (## ... or non-empty line)
    """
    lines = text.splitlines()
    tables = []
    i = 0
    n = len(lines)
    sep_re = re.compile(r"^\s*\|\s*[:\-]{1,}\s*\|")

    while i < n:
        if "|" in lines[i]:
            # potential header line; check next line for separator
            if i + 1 < n and re.search(r"^\s*\|\s*[:\-]+", lines[i + 1]):
                start = i
                j = i + 2
                table_lines = [lines[start], lines[i + 1]]
                while j < n and "|" in lines[j]:
                    # stop if the line is purely a markdown horizontal rule or a section break
                    if lines[j].strip() == "---":
                        break
                    table_lines.append(lines[j])
                    j += 1

                # find nearest heading above the table
                heading = None
                k = start - 1
                while k >= 0:
                    s = lines[k].strip()
                    if s == "":
                        k -= 1
                        continue
                    if s.startswith("#"):
                        heading = s.lstrip("#").strip()
                        break
                    # accept lines that look like section titles
                    if len(s) < 120 and (
                        s.lower().startswith("forward")
                        or s.lower().startswith("reverse")
                        or "percobaan" in s.lower()
                        or "data" in s.lower()
                    ):
                        heading = s
                        break
                    k -= 1

                tables.append({"heading": heading or "", "lines": table_lines})
                i = j
                continue
        i += 1
    return tables


def split_row(line: str) -> List[str]:
    # remove leading/trailing pipe and split; keep inner empty cells
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_table(table_lines: List[str]) -> Optional[Tuple[List[str], List[List[str]]]]:
    if len(table_lines) < 2:
        return None
    header = split_row(table_lines[0])
    # data rows start after the separator (line 1)
    rows = []
    for row in table_lines[2:]:
        if "|" not in row:
            continue
        cells = split_row(row)
        # ignore separator-like rows
        if all(re.match(r"^[:\-\s]+$", c) for c in cells):
            continue
        rows.append(cells)
    return header, rows


def parse_number(s: str) -> Optional[float]:
    if s is None:
        return None
    s = s.strip()
    if s == "":
        return None
    # remove asterisk notes and non-breaking spaces
    s = s.replace("*", "").replace("\xa0", " ")
    # replace comma decimal with dot
    # but be careful: thousands separator not expected in these data sets
    s = s.replace(" ", "")
    s = s.replace(",", ".")
    # try direct conversion
    try:
        return float(s)
    except Exception:
        # try to extract first numeric token
        m = re.search(r"[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?", s)
        if m:
            try:
                return float(m.group(0))
            except Exception:
                return None
    return None


def slugify(s: str) -> str:
    s = s or "table"
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "table"


def plot_xy(
    x,
    y,
    title: str,
    xlabel: str,
    ylabel: str,
    outpath: Optional[str] = None,
    show: bool = True,
):
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(x, y, marker="o", linestyle="-", color="C0")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    if outpath:
        fig.savefig(outpath, dpi=200)
        print(f"Saved plot: {outpath}")
    if show:
        plt.show()
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", "-i", default="praktikum_5/datakita.qmd", help="Path to datakita.qmd"
    )
    parser.add_argument(
        "--outdir", "-o", default="plots", help="Output directory for saved plots"
    )
    # by default do not show plots (save-only mode); use --show to display
    parser.add_argument(
        "--show",
        dest="show",
        action="store_true",
        help="Show plots interactively",
    )
    # enforce PNG output only per user's request
    # (no --format option; files will be saved with .png extension)
    args = parser.parse_args()

    text = read_file(args.input)
    tables = find_tables(text)
    if not tables:
        print("No markdown tables found in the input file.")
        return

    os.makedirs(args.outdir, exist_ok=True)

    plotted = 0
    for idx, t in enumerate(tables, start=1):
        parsed = parse_table(t["lines"])
        heading = t.get("heading") or ""
        if not parsed:
            continue
        header, rows = parsed
        # normalize headers for matching
        header_norm = [h.lower() for h in header]

        # find indices for Arus and V dioda
        idx_arus = None
        idx_vd = None
        for i, h in enumerate(header_norm):
            if "arus" in h:
                idx_arus = i
            if "diod" in h or ("v" in h and "diod" in h):
                idx_vd = i
            # some headers may be like 'v dioda (v)'
            if "v diod" in h or "v_diod" in h or "v dioda" in h:
                idx_vd = i

        # if Arus and V dioda found -> plot them
        if idx_arus is not None and idx_vd is not None:
            xs = []
            ys = []
            for r in rows:
                # guard index errors
                if idx_arus >= len(r) or idx_vd >= len(r):
                    continue
                a = parse_number(r[idx_arus])
                v = parse_number(r[idx_vd])
                if a is None or v is None:
                    continue
                xs.append(a)
                ys.append(v)
            if xs and ys:
                title = (
                    f"{heading} - Arus vs V dioda"
                    if heading
                    else f"Table {idx} - Arus vs V dioda"
                )
                fname = f"{idx:02d}_{slugify(heading or 'arus_vd')}.png"
                outpath = os.path.join(args.outdir, fname)
                plot_xy(
                    xs,
                    ys,
                    title,
                    "Arus (mA)",
                    "V dioda (V)",
                    outpath=outpath,
                    show=args.show,
                )
                plotted += 1
            else:
                print(f"Skipped table '{heading}': no numeric Arus/V dioda rows parsed")
            continue

        # otherwise, try to detect Volt Input vs Vrms D/R (Percobaan 2)
        idx_volt = None
        idx_vrms_d = None
        idx_vrms_r = None
        for i, h in enumerate(header_norm):
            if "volt" in h or "tegangan" in h:
                idx_volt = i
            if (
                "vrms d" in h
                or ("vrms" in h and "d" in h)
                or ("vrms" in h and "d" in header_norm)
            ):
                idx_vrms_d = i
            if (
                "vrms r" in h
                or ("vrms" in h and "r" in h)
                or ("vrms" in h and "r" in header_norm)
            ):
                idx_vrms_r = i
            # fallback: Vrms columns often contain 'vrms' and 'd' or 'r'
            if "vrms d" in h:
                idx_vrms_d = i
            if "vrms r" in h:
                idx_vrms_r = i

        if idx_volt is not None and (idx_vrms_d is not None or idx_vrms_r is not None):
            xs = []
            ys_d = []
            ys_r = []
            for r in rows:
                if idx_volt >= len(r):
                    continue
                xv = parse_number(r[idx_volt])
                if xv is None:
                    continue
                xs.append(xv)
                if idx_vrms_d is not None and idx_vrms_d < len(r):
                    ys_d.append(parse_number(r[idx_vrms_d]))
                else:
                    ys_d.append(None)
                if idx_vrms_r is not None and idx_vrms_r < len(r):
                    ys_r.append(parse_number(r[idx_vrms_r]))
                else:
                    ys_r.append(None)

            # plot Vrms D if present
            if idx_vrms_d is not None:
                ys = [y for y in ys_d if y is not None]
                xs_for_ys = [x for x, y in zip(xs, ys_d) if y is not None]
                if xs_for_ys:
                    title = (
                        f"{heading} - Volt Input vs Vrms D"
                        if heading
                        else f"Table {idx} - Volt vs Vrms D"
                    )
                    fname = f"{idx:02d}_{slugify(heading or 'volt')}_vrms_d.png"
                    outpath = os.path.join(args.outdir, fname)
                    plot_xy(
                        xs_for_ys,
                        ys,
                        title,
                        "Volt Input (V)",
                        "Vrms D (V)",
                        outpath=outpath,
                        show=args.show,
                    )
                    plotted += 1

            if idx_vrms_r is not None:
                ys = [y for y in ys_r if y is not None]
                xs_for_ys = [x for x, y in zip(xs, ys_r) if y is not None]
                if xs_for_ys:
                    title = (
                        f"{heading} - Volt Input vs Vrms R"
                        if heading
                        else f"Table {idx} - Volt vs Vrms R"
                    )
                    fname = f"{idx:02d}_{slugify(heading or 'volt')}_vrms_r.png"
                    outpath = os.path.join(args.outdir, fname)
                    plot_xy(
                        xs_for_ys,
                        ys,
                        title,
                        "Volt Input (V)",
                        "Vrms R (V)",
                        outpath=outpath,
                        show=args.show,
                    )
                    plotted += 1
            continue

        # special-case: table with Komponen | Y1 | Y2 -> grouped bar chart
        header_norm = [h.lower() for h in header]
        idx_komponen = next(
            (i for i, h in enumerate(header_norm) if "komponen" in h), None
        )
        idx_y1 = next((i for i, h in enumerate(header_norm) if "y1" in h), None)
        idx_y2 = next((i for i, h in enumerate(header_norm) if "y2" in h), None)
        if idx_komponen is not None and (idx_y1 is not None or idx_y2 is not None):
            labels = []
            y1vals = []
            y2vals = []
            for r in rows:
                if idx_komponen >= len(r):
                    continue
                labels.append(r[idx_komponen])
                y1vals.append(
                    parse_number(r[idx_y1])
                    if idx_y1 is not None and idx_y1 < len(r)
                    else None
                )
                y2vals.append(
                    parse_number(r[idx_y2])
                    if idx_y2 is not None and idx_y2 < len(r)
                    else None
                )

            # filter out rows with no numeric data
            filt_labels = []
            filt_y1 = []
            filt_y2 = []
            for lbl, a, b in zip(labels, y1vals, y2vals):
                if a is None and b is None:
                    continue
                filt_labels.append(lbl)
                # replace missing with 0 for plotting, but could also use None
                filt_y1.append(a if a is not None else 0.0)
                filt_y2.append(b if b is not None else 0.0)

            if filt_labels:
                fig, ax = plt.subplots(figsize=(7, 5))
                x_pos = list(range(len(filt_labels)))
                width = 0.35
                ax.bar([p - width / 2 for p in x_pos], filt_y1, width, label="Y1")
                ax.bar([p + width / 2 for p in x_pos], filt_y2, width, label="Y2")
                ax.set_xticks(x_pos)
                ax.set_xticklabels(filt_labels)
                ax.set_ylabel("Voltage (V)")
                ax.set_title(f"{heading} - Y1 vs Y2")
                ax.legend()
                plt.tight_layout()
                fname = f"{idx:02d}_{slugify(heading or 'komponen_y1_y2')}_bar.png"
                outpath = os.path.join(args.outdir, fname)
                fig.savefig(outpath, dpi=200)
                print(f"Saved plot: {outpath}")
                if args.show:
                    plt.show()
                plt.close(fig)
                plotted += 1
                continue

        # skip trivial tables (single column) silently
        if len(header) <= 1:
            continue

        # nothing matched
        print(f"No matching columns found for table '{heading}' (headers: {header})")

    if plotted == 0:
        print(
            "No plots were created. Make sure the input file contains 'Arus' and 'V dioda' columns or Volt/Vrms columns."
        )


if __name__ == "__main__":
    main()
