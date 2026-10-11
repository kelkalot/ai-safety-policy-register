#!/usr/bin/env python3
"""A small, reproducible analysis of the register, run straight from data/register.sqlite.

    python3 examples/analysis.py                 # writes examples/output/analysis.md (+ a PNG chart if matplotlib is installed)
    python3 examples/analysis.py --db other.sqlite --out some/folder

It answers seven questions with plain SQL and the standard library, so it works anywhere
the register does. matplotlib is optional and only used for the chart. Use it as a
starting point for your own questions: every section is one query.

Reading notes
- date_published may be a partial date (YYYY-MM or YYYY) when the source gives no exact
  day. Year-level questions use substr(date, 1, 4); day-level questions require full dates.
- safety_topics are normalised into the `topics` table (one row per record and topic), so
  counting topics is a plain GROUP BY rather than string splitting.
"""
import argparse
import sqlite3
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORCES = ["Binding", "Non-binding", "Proposed"]


def md_table(headers, rows):
    """Render a list of rows as a Markdown table; numbers are right-aligned."""
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---:" if isinstance(v, (int, float)) else "---" for v in (rows[0] if rows else headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(("%.0f%%" % v if isinstance(v, float) else str(v)) for v in r) + " |")
    return "\n".join(out)


def q(con, sql, *params):
    return con.execute(sql, params).fetchall()


def run(db_path, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    meta = dict(q(con, "SELECT key, value FROM meta"))
    sections = []

    # 1. Headline figures ---------------------------------------------------------------------
    total = q(con, "SELECT COUNT(*) FROM records")[0][0]
    by_force = dict(q(con, "SELECT legal_force, COUNT(*) FROM records GROUP BY 1"))
    countries = q(con, "SELECT COUNT(DISTINCT country) FROM records WHERE jurisdiction_level IN ('National','Sub-national')")[0][0]
    bodies = q(con, "SELECT COUNT(DISTINCT jurisdiction) FROM records")[0][0]
    sections.append("## 1. Headline figures\n\n" + md_table(
        ["Measure", "Value"],
        [["Records", total], ["Binding", by_force.get("Binding", 0)], ["Non-binding", by_force.get("Non-binding", 0)],
         ["Proposed", by_force.get("Proposed", 0)], ["Countries with national or sub-national instruments", countries],
         ["Distinct jurisdictions and bodies", bodies]]))

    # 2. Growth: instruments per year by legal force ------------------------------------------
    rows = q(con, """SELECT substr(date_published,1,4) AS y,
                            SUM(legal_force='Binding'), SUM(legal_force='Non-binding'), SUM(legal_force='Proposed'), COUNT(*)
                     FROM records WHERE date_published IS NOT NULL GROUP BY 1 ORDER BY 1""")
    sections.append("## 2. Instruments per year of publication, by legal force\n\n"
                    "Year = first four characters of `date_published`, so partial dates count too. "
                    "%d records have no date and are left out.\n\n" % q(con, "SELECT COUNT(*) FROM records WHERE date_published IS NULL")[0][0]
                    + md_table(["Year", "Binding", "Non-binding", "Proposed", "Total"], [list(r) for r in rows]))

    # 3. Regions: how much of each region's output is binding ---------------------------------
    region_rows = q(con, """SELECT region, COUNT(*) AS n, SUM(legal_force='Binding') AS b,
                                   SUM(legal_force='Non-binding') AS nb, SUM(legal_force='Proposed') AS p
                            FROM records GROUP BY 1 ORDER BY n DESC""")
    sections.append("## 3. Regions\n\n" + md_table(
        ["Region", "Records", "Binding", "Non-binding", "Proposed", "Binding share"],
        [[r[0], r[1], r[2], r[3], r[4], 100.0 * r[2] / r[1]] for r in region_rows]))

    # 4. Topics by legal force ------------------------------------------------------------------
    topic_rows = q(con, """SELECT t.topic, COUNT(*) AS n, SUM(r.legal_force='Binding'), SUM(r.legal_force='Non-binding'),
                                  SUM(r.legal_force='Proposed')
                           FROM topics t JOIN records r ON r.id = t.record_id GROUP BY 1 ORDER BY n DESC""")
    sections.append("## 4. Safety topics, by legal force\n\nA record can carry several topics, so columns do not sum to the record count.\n\n"
                    + md_table(["Topic", "Records", "Binding", "Non-binding", "Proposed"], [list(r) for r in topic_rows]))

    # 5. Which topics travel together -----------------------------------------------------------
    pair_rows = q(con, """SELECT a.topic, b.topic, COUNT(*) AS n FROM topics a JOIN topics b
                          ON a.record_id = b.record_id AND a.topic < b.topic GROUP BY 1, 2 ORDER BY n DESC LIMIT 10""")
    sections.append("## 5. Topic pairs that most often appear in the same instrument\n\n"
                    + md_table(["Topic A", "Topic B", "Records"], [list(r) for r in pair_rows]))

    # 6. How long from publication to entry into force (binding instruments with full dates) ---
    gaps = q(con, """SELECT id, short_title, date_published, date_in_force,
                            CAST(julianday(date_in_force) - julianday(date_published) AS INTEGER) AS days
                     FROM records WHERE legal_force='Binding' AND length(date_published)=10 AND length(date_in_force)=10
                     ORDER BY days""")
    days = [g[4] for g in gaps]
    if days:
        qs = statistics.quantiles(days, n=4) if len(days) >= 4 else [None] * 3
        summary = md_table(["Measure", "Days"], [["Instruments with both dates", len(days)], ["Minimum", min(days)],
                                                 ["Lower quartile", int(qs[0]) if qs[0] is not None else "-"],
                                                 ["Median", int(statistics.median(days))],
                                                 ["Upper quartile", int(qs[2]) if qs[2] is not None else "-"], ["Maximum", max(days)]])
        extremes = md_table(["ID", "Instrument", "Published", "In force", "Days"],
                            [list(g) for g in gaps[:3]] + [list(g) for g in gaps[-3:]])
        sections.append("## 6. Time from publication to entry into force (binding instruments)\n\n"
                        "Only records with a full `date_published` and `date_in_force` are counted. Negative values are instruments "
                        "that took effect before formal publication; large values are phased laws whose first obligations apply much later.\n\n"
                        + summary + "\n\nShortest three and longest three:\n\n" + extremes)

    # 7. Evidence quality: verification and local copies ------------------------------------------
    ver = q(con, "SELECT verification_level, COUNT(*) FROM records GROUP BY 1 ORDER BY 1")
    loc = q(con, "SELECT local_status, COUNT(*) FROM records GROUP BY 1 ORDER BY 2 DESC")
    pdfs = q(con, "SELECT COUNT(DISTINCT record_id) FROM archive_files WHERE path LIKE '%.pdf' AND integrity='ok'")[0][0]
    sections.append("## 7. Evidence behind the records\n\n" + md_table(["Verification level", "Records"], [list(r) for r in ver])
                    + "\n\n" + md_table(["Local copy status", "Records"], [list(r) for r in loc])
                    + "\n\nRecords with at least one locally stored PDF: %d of %d." % (pdfs, total))

    # Chart: region x legal force --------------------------------------------------------------
    chart_note = ""
    try:
        chart_path = draw_region_chart(region_rows, out_dir / "instruments-by-region.png")
        chart_note = "\n\n![Instruments by region and legal force](%s)\n" % chart_path.name
    except ImportError:
        chart_note = "\n\n(Install matplotlib to also get the chart `instruments-by-region.png`.)\n"

    head = ("# %s: analysis example\n\nSnapshot %s, version %s, %d records. Generated by `examples/analysis.py` from `data/register.sqlite`.\n"
            % (meta.get("name", "Register"), meta.get("snapshot_date", "?"), meta.get("version", "?"), total))
    text = head + chart_note + "\n" + "\n\n".join(sections) + "\n"
    (out_dir / "analysis.md").write_text(text, encoding="utf-8")
    return out_dir / "analysis.md"


def draw_region_chart(region_rows, path):
    """Horizontal stacked bars: records per region split by legal force.

    Colour and mark choices follow a validated categorical palette (slots 1-3, light mode):
    fixed series order, thin bars, 2px surface-coloured gaps between segments, hairline grid,
    text in neutral ink, a legend plus sparing direct labels (totals only).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
    SERIES = {"Binding": "#2a78d6", "Non-binding": "#eb6834", "Proposed": "#1baf7a"}
    rows = sorted(region_rows, key=lambda r: r[1])  # smallest at the bottom of the list = top of the chart reversed
    labels = [r[0] for r in rows]
    values = {"Binding": [r[2] for r in rows], "Non-binding": [r[3] for r in rows], "Proposed": [r[4] for r in rows]}
    totals = [r[1] for r in rows]

    fig_h = 0.42 * len(rows) + 1.3
    fig, ax = plt.subplots(figsize=(8.5, fig_h), dpi=150)
    fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
    left = [0] * len(rows)
    for name in FORCES:
        ax.barh(labels, values[name], left=left, height=0.56, color=SERIES[name], label=name,
                edgecolor=SURFACE, linewidth=1.5)  # the surface-coloured edge is the 2px gap between segments
        left = [a + b for a, b in zip(left, values[name])]
    for y, t in enumerate(totals):  # direct labels: totals only
        ax.text(t + 0.6, y, str(t), va="center", ha="left", fontsize=9, color=INK2)
    ax.set_xlim(0, max(totals) * 1.12)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(axis="both", colors=INK2, labelsize=9, length=0)
    ax.set_xlabel("Instruments in the register", color=INK2, fontsize=9)
    ax.set_title("Instruments by region and legal force", loc="left", color=INK, fontsize=11, fontweight="bold", pad=12)
    leg = ax.legend(loc="lower right", frameon=False, fontsize=9, labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run the example analysis on the register's SQLite file.")
    ap.add_argument("--db", default=str(ROOT / "data" / "register.sqlite"))
    ap.add_argument("--out", default=str(ROOT / "examples" / "output"))
    args = ap.parse_args(argv)
    if not Path(args.db).is_file():
        print("No database at %s. Run python3 tools/build.py first." % args.db); return 1
    out = run(Path(args.db), Path(args.out))
    print("Wrote", out.relative_to(ROOT) if str(out).startswith(str(ROOT)) else out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
