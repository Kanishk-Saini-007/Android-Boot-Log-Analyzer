"""Report generator: JSON for machines, a self-contained HTML page for humans.

The HTML report needs no build step and no network: one file, inline CSS,
no JavaScript - open it in any browser.
"""
from __future__ import annotations

import html
import json
from typing import List

from .classifier import CATEGORY_LABELS
from .models import BootTiming, Issue

SEVERITY_COLORS = {
    "CRITICAL": "#ff4d5e",
    "ERROR": "#ff8c42",
    "WARNING": "#ffd447",
}


def build_report(source_name: str, issues: List[Issue],
                 timing: BootTiming, summary: dict) -> dict:
    """The canonical report dictionary (also the JSON output)."""
    recommendations = []
    for issue in issues:
        if issue.recommendation not in recommendations:
            recommendations.append(issue.recommendation)
    if timing.slow_stages:
        note = ("Investigate slow boot stages: "
                + ", ".join(f"{s.name} ({s.duration:.1f}s)"
                            for s in timing.slow_stages))
        if note not in recommendations:
            recommendations.append(note)
    return {
        "tool": "android-boot-log-analyzer",
        "input": source_name,
        "summary": {
            "issues_detected": summary["issues_detected"],
            "total_boot_time_seconds": timing.duration,
            "counts_by_severity": summary["counts_by_severity"],
            "counts_by_category": summary["counts_by_category"],
        },
        "boot_timing": {
            "duration_seconds": timing.duration,
            "note": timing.note,
            "stages": [
                {"name": s.name, "start": s.start, "end": s.end,
                 "duration": s.duration, "slow": s.slow, "note": s.note}
                for s in timing.stages
            ],
        },
        "issues": [
            {
                "severity": i.severity,
                "category": i.category,
                "message": i.message,
                "recommendation": i.recommendation,
                "timestamp": i.timestamp,
                "tag": i.tag,
                "line_number": i.line_number,
            }
            for i in issues
        ],
        "recommendations": recommendations,
    }


def write_json(report: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")


def render_html(report: dict) -> str:
    e = html.escape
    summary = report["summary"]
    sev = summary["counts_by_severity"]
    cat = summary["counts_by_category"]

    cat_rows = "".join(
        f"<tr><td>{e(CATEGORY_LABELS.get(k, k.title()))}</td><td>{v}</td></tr>"
        for k, v in sorted(cat.items(), key=lambda kv: -kv[1])) or \
        "<tr><td colspan='2' class='muted'>No issues</td></tr>"

    issue_cards = []
    for i in report["issues"]:
        color = SEVERITY_COLORS.get(i["severity"], "#ffd447")
        ts = f"t+{i['timestamp']:.3f}s" if i["timestamp"] is not None else "n/a"
        issue_cards.append(
            f"<div class='issue' style='border-left-color:{color}'>"
            f"<div class='issue-head'><span class='badge' "
            f"style='background:{color}'>{i['severity']}</span> "
            f"<span class='cat'>{e(CATEGORY_LABELS.get(i['category'], i['category']))}</span>"
            f"<span class='ts'>{e(ts)} · line {i['line_number']}"
            + (f" · {e(i['tag'])}" if i["tag"] else "")
            + f"</span></div>"
            f"<div class='msg'>{e(i['message'])}</div>"
            f"<div class='rec'>&#8594; {e(i['recommendation'])}</div></div>")
    issues_html = "".join(issue_cards) or \
        "<p class='muted'>No errors or warnings detected. Clean boot.</p>"

    stage_rows = "".join(
        f"<tr class={'slow' if s['slow'] else ''}>"
        f"<td>{e(s['name'].replace('_', ' '))}</td>"
        f"<td>{s['start']:.2f}s</td><td>{s['end']:.2f}s</td>"
        f"<td>{s['duration']:.2f}s</td>"
        f"<td>{'SLOW' if s['slow'] else ''}</td></tr>"
        for s in report["boot_timing"]["stages"])

    recs = "".join(f"<li>{e(r)}</li>" for r in report["recommendations"]) or \
        "<li>Nothing to fix based on this log.</li>"

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Boot Diagnostic Report - {e(report['input'])}</title>
<style>
:root {{ --bg:#0b0f14; --card:#131a22; --line:#223040; --text:#e6edf3;
  --muted:#8b98a5; --lime:#a3e635; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text);
  font:15px/1.55 -apple-system,'Segoe UI',Roboto,sans-serif; }}
.wrap {{ max-width:1020px; margin:0 auto; padding:32px 20px 64px; }}
h1 {{ font-size:26px; margin:0 0 4px; }}
h2 {{ font-size:18px; margin:34px 0 12px; color:var(--lime); }}
.sub {{ color:var(--muted); margin-bottom:24px; }}
.cards {{ display:flex; flex-wrap:wrap; gap:14px; }}
.card {{ background:var(--card); border:1px solid var(--line);
  border-radius:12px; padding:16px 20px; min-width:150px; flex:1; }}
.card .num {{ font-size:30px; font-weight:700; }}
.card .lbl {{ color:var(--muted); font-size:12.5px; text-transform:uppercase;
  letter-spacing:.06em; }}
table {{ width:100%; border-collapse:collapse; background:var(--card);
  border-radius:12px; overflow:hidden; }}
th, td {{ text-align:left; padding:9px 14px; border-bottom:1px solid var(--line); }}
th {{ color:var(--muted); font-size:12px; text-transform:uppercase;
  letter-spacing:.05em; }}
tr.slow td {{ color:#ff8c42; }}
.issue {{ background:var(--card); border:1px solid var(--line);
  border-left:4px solid; border-radius:10px; padding:12px 16px;
  margin:10px 0; }}
.badge {{ color:#0b0f14; font-weight:700; font-size:11px; border-radius:6px;
  padding:2px 8px; }}
.cat {{ font-weight:600; margin-left:8px; }}
.ts {{ color:var(--muted); font-size:12.5px; margin-left:10px; }}
.msg {{ font-family:ui-monospace,Menlo,Consolas,monospace; font-size:13px;
  margin:8px 0 6px; word-break:break-word; }}
.rec {{ color:var(--muted); font-size:13px; }}
.muted {{ color:var(--muted); }}
footer {{ margin-top:40px; color:var(--muted); font-size:12.5px; }}
</style></head>
<body><div class="wrap">
<h1>Boot Diagnostic Report</h1>
<div class="sub">Input: <code>{e(report['input'])}</code></div>

<div class="cards">
  <div class="card"><div class="num">{summary['issues_detected']}</div>
    <div class="lbl">Issues detected</div></div>
  <div class="card"><div class="num">{summary['total_boot_time_seconds'] if summary['total_boot_time_seconds'] is not None else 'n/a'}{'' if summary['total_boot_time_seconds'] is None else 's'}</div>
    <div class="lbl">Total boot time</div></div>
  <div class="card"><div class="num">{sev.get('CRITICAL', 0)} / {sev.get('ERROR', 0)} / {sev.get('WARNING', 0)}</div>
    <div class="lbl">Critical / Error / Warning</div></div>
</div>

{f"<h2>Boot stages</h2><table><tr><th>Stage</th><th>Start</th><th>End</th><th>Duration</th><th></th></tr>{stage_rows}</table>" if stage_rows else ''}

<h2>Issues by category</h2>
<table><tr><th>Category</th><th>Count</th></tr>{cat_rows}</table>

<h2>Detected issues</h2>
{issues_html}

<h2>Recommendations</h2>
<ul>{recs}</ul>

<footer>Generated by <strong>android-boot-log-analyzer</strong> · rule-based,
fully explainable output · built by Kanishk Saini as a learning project</footer>
</div></body></html>"""


def write_html(report: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_html(report))
