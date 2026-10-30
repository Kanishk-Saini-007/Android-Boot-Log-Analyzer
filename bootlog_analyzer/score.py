"""Boot Health Score: a transparent 0-100 grade for a boot log.

The score is deliberately simple and fully explained in the report - no
magic numbers appear without the math behind them.

    start at 100
    -25 per CRITICAL issue
    -10 per ERROR issue
    -3  per WARNING issue
    -5  per slow boot stage (max -15)
    floor at 0
"""
from __future__ import annotations

from typing import List

from .models import BootTiming, Issue

PENALTIES = {"CRITICAL": 25, "ERROR": 10, "WARNING": 3}
SLOW_STAGE_PENALTY = 5
SLOW_STAGE_CAP = 15


def health_score(issues: List[Issue], timing: BootTiming) -> dict:
    breakdown = []
    score = 100
    for severity in ("CRITICAL", "ERROR", "WARNING"):
        count = sum(1 for i in issues if i.severity == severity)
        if count:
            lost = count * PENALTIES[severity]
            score -= lost
            breakdown.append(
                f"{count} x {severity} (-{PENALTIES[severity]} each) = -{lost}")
    slow = len(timing.slow_stages)
    if slow:
        lost = min(slow * SLOW_STAGE_PENALTY, SLOW_STAGE_CAP)
        score -= lost
        breakdown.append(
            f"{slow} x slow stage (-{SLOW_STAGE_PENALTY} each, capped) = -{lost}")
    score = max(0, score)
    if score >= 90:
        grade = "Excellent"
    elif score >= 70:
        grade = "Good"
    elif score >= 40:
        grade = "Needs attention"
    else:
        grade = "Critical"
    return {"score": score, "grade": grade, "breakdown": breakdown}
