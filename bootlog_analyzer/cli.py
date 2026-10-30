"""Command line interface.

Usage:
    python -m bootlog_analyzer analyze <logfile> [--html PATH] [--json PATH]
    python -m bootlog_analyzer compare <old.log> <new.log>
    python -m bootlog_analyzer <logfile>            (same as analyze)
"""
from __future__ import annotations

import argparse
import sys

from .boot_time import analyze as analyze_timing
from .compare import compare_issues, verdict
from .detector import detect, summarize
from .parser import parse_file
from .report import build_report, write_html, write_json
from .score import health_score


def _run_pipeline(path: str):
    entries = parse_file(path)
    issues = detect(entries)
    timing = analyze_timing(entries)
    summary = summarize(issues)
    health = health_score(issues, timing)
    report = build_report(path, issues, timing, summary, health)
    return report, issues, timing, health


def _print_console(report: dict) -> None:
    s = report["summary"]
    cat = s["counts_by_category"]
    print("\nBoot Diagnostic Report")
    print("=" * 40)
    print(f"{s['issues_detected']} issue(s) detected")
    if s["total_boot_time_seconds"] is not None:
        print(f"* Total boot time: {s['total_boot_time_seconds']:.1f} seconds")
    for name, label in (("kernel", "Kernel"), ("driver", "Driver"),
                        ("firmware", "Firmware"), ("selinux", "SELinux"),
                        ("system", "System"), ("other", "Other")):
        if cat.get(name):
            plural = "s" if cat[name] != 1 else ""
            print(f"* {label} issue{plural}: {cat[name]}")
    print(f"* Boot Health Score: {s['boot_health_score']}/100 "
          f"({s['boot_health_grade']})")
    slow = [st for st in report["boot_timing"]["stages"] if st["slow"]]
    if slow:
        print("\nSlow boot stages:")
        for st in slow:
            print(f"* {st['name']}: {st['duration']:.1f}s")
    if report["recommendations"]:
        print("\nRecommendations")
        for rec in report["recommendations"]:
            print(f"* {rec}")
    print()


def _cmd_analyze(args) -> int:
    report, _, _, _ = _run_pipeline(args.logfile)
    if args.json:
        write_json(report, args.json)
    if args.html:
        write_html(report, args.html)
    _print_console(report)
    written = [p for p in (args.json, args.html) if p]
    if written:
        print("Report written to: " + ", ".join(written))
    return 0


def _cmd_compare(args) -> int:
    old_report, old_issues, old_timing, old_health = _run_pipeline(args.old)
    new_report, new_issues, new_timing, new_health = _run_pipeline(args.new)
    diff = compare_issues(old_issues, new_issues)

    print("\nBoot Comparison Report")
    print("=" * 40)
    for line in verdict(old_health, new_health,
                        old_timing.duration, new_timing.duration):
        print(f"* {line}")
    print(f"* Fixed issues: {diff['summary']['fixed']}")
    print(f"* New issues: {diff['summary']['introduced']}")
    print(f"* Persisting issues: {diff['summary']['persisting']}")
    if diff["introduced"]:
        print("\nNew issues to look at:")
        for issue in diff["introduced"]:
            print(f"* [{issue.severity}] ({issue.category}) {issue.message}")
    if diff["fixed"]:
        print("\nFixed since last boot:")
        for issue in diff["fixed"]:
            print(f"* [{issue.severity}] ({issue.category}) {issue.message}")
    if args.json:
        write_json({
            "old": args.old, "new": args.new,
            "verdict": verdict(old_health, new_health,
                               old_timing.duration, new_timing.duration),
            "summary": diff["summary"],
            "introduced": [
                {"severity": i.severity, "category": i.category,
                 "message": i.message} for i in diff["introduced"]],
            "fixed": [
                {"severity": i.severity, "category": i.category,
                 "message": i.message} for i in diff["fixed"]],
        }, args.json)
        print(f"\nComparison written to: {args.json}")
    print()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="bootlog_analyzer",
        description="Analyze Android boot logs (dmesg/logcat): detect errors, "
                    "classify them, measure boot stages and generate reports.")
    sub = parser.add_subparsers(dest="command")

    p_an = sub.add_parser("analyze", help="Analyze one boot log")
    p_an.add_argument("logfile")
    p_an.add_argument("--json", default="report.json",
                      help="JSON report path (default: report.json; '' to skip)")
    p_an.add_argument("--html", default="report.html",
                      help="HTML report path (default: report.html; '' to skip)")
    p_an.set_defaults(func=_cmd_analyze)

    p_cmp = sub.add_parser("compare", help="Compare two boot logs")
    p_cmp.add_argument("old")
    p_cmp.add_argument("new")
    p_cmp.add_argument("--json", default=None, help="Optional JSON output path")
    p_cmp.set_defaults(func=_cmd_compare)

    # Bare `python -m bootlog_analyzer <file>` behaves like `analyze <file>`.
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] not in ("analyze", "compare") and not argv[0].startswith("-"):
        argv = ["analyze"] + argv
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
