from bootlog_analyzer.models import BootTiming, Issue
from bootlog_analyzer.score import health_score


def _issue(sev):
    return Issue(severity=sev, category="kernel", message="m",
                 recommendation="r")


def test_perfect_boot_scores_100():
    result = health_score([], BootTiming())
    assert result["score"] == 100
    assert result["grade"] == "Excellent"


def test_penalty_math_is_exact():
    issues = [_issue("CRITICAL"), _issue("ERROR"), _issue("ERROR"),
              _issue("WARNING")]
    result = health_score(issues, BootTiming())
    assert result["score"] == 100 - 25 - 10 - 10 - 3
    assert len(result["breakdown"]) == 3


def test_score_floors_at_zero():
    issues = [_issue("CRITICAL")] * 10
    assert health_score(issues, BootTiming())["score"] == 0
