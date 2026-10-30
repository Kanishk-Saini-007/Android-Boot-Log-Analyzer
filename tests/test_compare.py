from bootlog_analyzer.compare import compare_issues
from bootlog_analyzer.models import Issue


def _issue(category, message):
    return Issue(severity="ERROR", category=category, message=message,
                 recommendation="r")


def test_fixed_introduced_persisting():
    old = [_issue("firmware", "load fw.bin failed pid 123"),
           _issue("driver", "i2c error")]
    new = [_issue("driver", "i2c error"),
           _issue("selinux", "avc: denied { read }")]
    diff = compare_issues(old, new)
    assert diff["summary"] == {"fixed": 1, "introduced": 1, "persisting": 1}
    # PIDs differ but the fingerprint must still match.
    assert diff["persisting"][0].category == "driver"
