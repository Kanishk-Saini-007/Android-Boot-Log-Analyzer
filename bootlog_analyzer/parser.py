"""Log reader: turns raw dmesg / logcat text into structured LogEntry objects.

Supported formats (auto-detected per file):

* logcat "threadtime":  ``10-30 09:15:04.123  1024  1024 E SurfaceFlinger: msg``
* logcat "brief"     :  ``E/SurfaceFlinger( 1024): msg``        (no timestamp)
* kernel dmesg       :  ``[   12.345678] some kernel message``

Lines that match nothing are kept as ``source='unknown'`` entries so the
detector can still scan them for keywords.
"""
from __future__ import annotations

import re
from typing import Iterable, List

from .models import LogEntry

_LOGCAT_THREADTIME = re.compile(
    r"^(?P<date>\d{2}-\d{2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\s+"
    r"(?P<pid>\d+)\s+(?P<tid>\d+)\s+"
    r"(?P<level>[VDIWEFS])\s+"
    r"(?P<tag>[^:]{1,64}):\s?(?P<msg>.*)$"
)

_LOGCAT_BRIEF = re.compile(
    r"^(?P<level>[VDIWEFS])/(?P<tag>[^(]{1,64})\(\s*(?P<pid>\d+)\):\s?(?P<msg>.*)$"
)

_DMESG = re.compile(r"^\[\s*(?P<ts>\d+\.\d+)\]\s*(?P<msg>.*)$")

_LOGCAT_LEVELS = {
    "V": "VERBOSE",
    "D": "DEBUG",
    "I": "INFO",
    "W": "WARNING",
    "E": "ERROR",
    "F": "CRITICAL",
    "S": "SILENT",
}

# Kernel messages do not carry a log level, so we infer one from the wording.
_KERNEL_CRITICAL = re.compile(
    r"kernel panic|oops|bug:|hard lockup|soft lockup|unable to mount root|"
    r"not syncing|stack-protector|watchdog.*fired",
    re.IGNORECASE,
)
_KERNEL_ERROR = re.compile(
    r"\berror\b|\bfailed\b|\bfailure\b|unable to|no such file|"
    r"call trace|avc:\s*denied",
    re.IGNORECASE,
)
_KERNEL_WARNING = re.compile(
    r"\bwarn|deprecated|falling back|tainted|will be removed|slow",
    re.IGNORECASE,
)


def _kernel_level(message: str) -> str:
    if _KERNEL_CRITICAL.search(message):
        return "CRITICAL"
    if _KERNEL_ERROR.search(message):
        return "ERROR"
    if _KERNEL_WARNING.search(message):
        return "WARNING"
    return "INFO"


def _hms_to_seconds(hms: str) -> float:
    hh, mm, rest = hms.split(":")
    return int(hh) * 3600 + int(mm) * 60 + float(rest)


def parse_lines(lines: Iterable[str]) -> List[LogEntry]:
    """Parse raw text lines into LogEntry objects.

    Timestamps are normalised so the first timestamped line of the file is
    t=0.0; this makes boot durations directly comparable across formats.
    """
    entries: List[LogEntry] = []
    t0 = None

    for raw_line in lines:
        line = raw_line.rstrip("\n")
        if not line.strip():
            continue

        m = _DMESG.match(line)
        if m:
            ts = float(m.group("ts"))
            msg = m.group("msg").strip()
            if t0 is None:
                t0 = ts
            entries.append(LogEntry(
                raw=line, source="dmesg", timestamp=round(ts - t0, 6),
                level=_kernel_level(msg), tag="", message=msg,
            ))
            continue

        m = _LOGCAT_THREADTIME.match(line)
        if m:
            ts = _hms_to_seconds(m.group("time"))
            if t0 is None:
                t0 = ts
            entries.append(LogEntry(
                raw=line, source="logcat", timestamp=round(ts - t0, 6),
                level=_LOGCAT_LEVELS[m.group("level")],
                tag=m.group("tag").strip(), message=m.group("msg").strip(),
            ))
            continue

        m = _LOGCAT_BRIEF.match(line)
        if m:
            entries.append(LogEntry(
                raw=line, source="logcat", timestamp=None,
                level=_LOGCAT_LEVELS[m.group("level")],
                tag=m.group("tag").strip(), message=m.group("msg").strip(),
            ))
            continue

        entries.append(LogEntry(
            raw=line, source="unknown", timestamp=None,
            level="INFO", tag="", message=line.strip(),
        ))

    return entries


def parse_text(text: str) -> List[LogEntry]:
    return parse_lines(text.splitlines())


def parse_file(path: str) -> List[LogEntry]:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return parse_lines(fh)
