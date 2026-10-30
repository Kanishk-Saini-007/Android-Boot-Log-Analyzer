from bootlog_analyzer.detector import detect, summarize
from bootlog_analyzer.parser import parse_text


def _issues(text):
    return detect(parse_text(text))


def test_detects_logcat_error_and_warning():
    issues = _issues(
        "10-30 09:15:00.000  1  1 I ok: fine\n"
        "10-30 09:15:01.000  1  1 W sys: disk getting full\n"
        "10-30 09:15:02.000  1  1 E sys: camera provider died\n")
    assert [i.severity for i in issues] == ["WARNING", "ERROR"]


def test_avc_denial_is_promoted_even_at_low_level():
    issues = _issues(
        "10-30 09:15:00.000  1  1 I audit: avc:  denied  { read } for pid=5\n")
    assert len(issues) == 1
    assert issues[0].severity == "ERROR"
    assert issues[0].category == "selinux"


def test_logcat_failed_keyword_is_flagged_as_warning():
    issues = _issues("10-30 09:15:00.000  1  1 I vold: mount failed quietly\n")
    assert len(issues) == 1
    assert issues[0].severity == "WARNING"


def test_suppression_rules_drop_known_noise():
    issues = _issues(
        "10-30 09:15:00.000  1  1 E x: avc: denied { getopt } for pid=9\n")
    assert issues == []


def test_summarize_counts():
    issues = _issues(
        "[    1.0] watchdog: BUG: soft lockup - CPU#2 stuck for 22s!\n"
        "[    2.0] i2c error: -107\n"
        "[    3.0] deprecated interface used\n")
    s = summarize(issues)
    assert s["issues_detected"] == 3
    assert s["counts_by_severity"] == {"CRITICAL": 1, "ERROR": 1, "WARNING": 1}
