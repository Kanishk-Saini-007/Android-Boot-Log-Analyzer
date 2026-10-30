"""Error detector: finds ERROR, WARNING and CRITICAL entries.

Logcat lines carry an explicit level. Kernel (dmesg) lines get their level
inferred by the parser. On top of that, two patterns are always promoted to
issues even if the surrounding level is low, because in practice they are
never benign during boot:

* SELinux denials (``avc: denied``)
* explicit ``failed`` / ``error`` wording in any logcat line
"""
from __future__ import annotations

import re
from typing import List

from .classifier import classify
from .models import Issue, LogEntry

_ALWAYS_FLAG = re.compile(r"avc:\s*denied", re.IGNORECASE)
_FLAG_IF_LOW_LEVEL = re.compile(r"\bfailed\b|\berror\b", re.IGNORECASE)

_ISSUE_LEVELS = {"WARNING", "ERROR", "CRITICAL"}

# Lines matching these are common, noisy and not real boot problems.
_SUPPRESS = re.compile(
    r"avc:\s*denied\s*\{\s*getopt|read.*battery.*sysfs", re.IGNORECASE
)


def detect(entries: List[LogEntry]) -> List[Issue]:
    issues: List[Issue] = []
    for idx, entry in enumerate(entries, start=1):
        level = entry.level
        flagged = level in _ISSUE_LEVELS
        if not flagged and _ALWAYS_FLAG.search(entry.message):
            flagged, level = True, "ERROR"
        if (
            not flagged
            and entry.source == "logcat"
            and _FLAG_IF_LOW_LEVEL.search(entry.message)
        ):
            flagged, level = True, "WARNING"
        if not flagged:
            continue
        if _SUPPRESS.search(entry.message):
            continue
        category, recommendation = classify(entry)
        issues.append(Issue(
            severity=level,
            category=category,
            message=entry.message,
            recommendation=recommendation,
            timestamp=entry.timestamp,
            tag=entry.tag,
            line_number=idx,
            raw=entry.raw,
        ))
    return issues


def summarize(issues: List[Issue]) -> dict:
    """Counts used by both the console output and the reports."""
    by_severity = {"CRITICAL": 0, "ERROR": 0, "WARNING": 0}
    by_category: dict = {}
    for issue in issues:
        by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
        by_category[issue.category] = by_category.get(issue.category, 0) + 1
    return {
        "issues_detected": len(issues),
        "counts_by_severity": by_severity,
        "counts_by_category": by_category,
    }
