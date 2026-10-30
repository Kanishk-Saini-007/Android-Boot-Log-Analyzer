import json
from pathlib import Path

from bootlog_analyzer.boot_time import analyze
from bootlog_analyzer.detector import detect, summarize
from bootlog_analyzer.parser import parse_file
from bootlog_analyzer.report import build_report, render_html, write_json
from bootlog_analyzer.score import health_score

SAMPLES = Path(__file__).resolve().parent.parent / "sample_logs"


def _report(name):
    entries = parse_file(str(SAMPLES / name))
    issues = detect(entries)
    timing = analyze(entries)
    return build_report(name, issues, timing, summarize(issues),
                        health_score(issues, timing))


def test_report_is_json_serializable(tmp_path):
    report = _report("boot_failure.log")
    out = tmp_path / "r.json"
    write_json(report, str(out))
    loaded = json.loads(out.read_text())
    assert loaded["summary"]["issues_detected"] > 0
    assert loaded["summary"]["counts_by_category"]["firmware"] >= 1


def test_html_contains_score_and_timeline():
    html = render_html(_report("boot_slow.log"))
    assert "Boot Diagnostic Report" in html
    assert "Boot Health Score" in html
    assert "<svg" in html  # the boot timeline
    assert "package scan" in html


def test_healthy_boot_has_no_issues():
    report = _report("boot_healthy.log")
    assert report["summary"]["issues_detected"] == 0
    assert report["summary"]["boot_health_score"] == 100
