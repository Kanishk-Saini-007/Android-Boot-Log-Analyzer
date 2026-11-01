"""Shared data structures."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LogEntry:
    """One parsed log line."""
    raw: str
    source: str                      # 'dmesg', 'logcat' or 'unknown'
    timestamp: Optional[float]       # seconds, relative to the first timestamped line
    level: str                       # VERBOSE, DEBUG, INFO, WARNING, ERROR, CRITICAL
    tag: str                         # logcat tag, '' for dmesg
    message: str


@dataclass
class Issue:
    """A detected problem worth showing in the report."""
    severity: str                    # WARNING, ERROR, CRITICAL
    category: str                    # kernel, driver, firmware, selinux, other
    message: str
    recommendation: str
    timestamp: Optional[float] = None
    tag: str = ""
    line_number: int = 0
    raw: str = ""


@dataclass
class BootStage:
    """One stage of the boot sequence with its measured duration."""
    name: str
    start: float
    end: float
    slow: bool = False
    note: str = ""

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 3)


@dataclass
class BootTiming:
    """Timing view of the whole boot."""
    duration: Optional[float] = None        # seconds from first to last timestamp
    stages: list = field(default_factory=list)
    slow_stages: list = field(default_factory=list)
    timestamps_found: bool = False
    note: str = ""
