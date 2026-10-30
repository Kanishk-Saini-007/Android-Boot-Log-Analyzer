"""Compare mode: diff two boot logs.

Answers the question every developer asks after a change: "did the boot get
better or worse?" It matches issues by (category, normalised message) and
reports which problems are new, which are fixed, and how the boot time and
health score moved.
"""
from __future__ import annotations

import re
from typing import List

from .models import Issue


def _fingerprint(issue: Issue) -> tuple:
    """Category + message with digits collapsed, so PIDs/timestamps do not
    defeat matching."""
    norm = re.sub(r"\d+", "#", issue.message.lower()).strip()
    return issue.category, norm


def compare_issues(old: List[Issue], new: List[Issue]) -> dict:
    old_map = {_fingerprint(i): i for i in old}
    new_map = {_fingerprint(i): i for i in new}
    fixed = [old_map[k] for k in old_map.keys() - new_map.keys()]
    introduced = [new_map[k] for k in new_map.keys() - old_map.keys()]
    persisting = [new_map[k] for k in old_map.keys() & new_map.keys()]
    return {
        "fixed": fixed,
        "introduced": introduced,
        "persisting": persisting,
        "summary": {
            "fixed": len(fixed),
            "introduced": len(introduced),
            "persisting": len(persisting),
        },
    }


def verdict(old_health: dict, new_health: dict,
            old_duration, new_duration) -> List[str]:
    lines = []
    delta = new_health["score"] - old_health["score"]
    if delta > 0:
        lines.append(f"Health score improved by {delta} points "
                     f"({old_health['score']} -> {new_health['score']}).")
    elif delta < 0:
        lines.append(f"Health score dropped by {-delta} points "
                     f"({old_health['score']} -> {new_health['score']}).")
    else:
        lines.append(f"Health score unchanged at {new_health['score']}.")
    if old_duration is not None and new_duration is not None:
        d = new_duration - old_duration
        if abs(d) >= 0.5:
            direction = "slower" if d > 0 else "faster"
            lines.append(f"Boot is {abs(d):.1f}s {direction} "
                         f"({old_duration:.1f}s -> {new_duration:.1f}s).")
        else:
            lines.append(f"Boot time roughly unchanged "
                         f"({old_duration:.1f}s -> {new_duration:.1f}s).")
    return lines
