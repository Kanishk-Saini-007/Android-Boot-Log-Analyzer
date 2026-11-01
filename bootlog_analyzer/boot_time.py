"""Boot time analyzer: measures how long each boot stage took.

Android emits well-known markers while booting. From logcat we read the
``boot_progress_*`` events and the ``sys.boot_completed=1`` property; from
dmesg we read kernel milestones. Every stage duration is the time between
two consecutive observed markers, so the numbers are explainable from the
log itself - nothing is estimated.

A stage is flagged slow when it takes longer than ``slow_threshold``
seconds (default 5s) and accounts for at least 10% of the boot.

Lines where the system itself prints a duration (``took 1450ms``,
``duration=2.1s``) are also reported as stages, using the printed value
directly - init actions and drivers often time themselves, and those
numbers are as explainable as marker-derived stages.

A marker-derived stage that would span (nearly) the whole log is dropped:
it means the log has no intermediate markers, not that one phase really
took the entire boot.
"""
from __future__ import annotations

from typing import List, Optional
import re

from .models import BootStage, BootTiming, LogEntry

# (stage name, substrings that mark its END). The first substring found in a
# message marks that point in time. Order defines the boot sequence.
STAGE_MARKERS = [
    ("kernel_start", ["boot: Linux version", "Linux version"]),
    ("kernel_init_done", ["Freeing unused kernel image", "Run /init as init process",
                          "Freeing unused kernel memory"]),
    ("init", ["init first stage", "init: init", "init started"]),
    ("selinux_setup", ["SELinux:  Initializing", "selinux:  SELinux"]),
    ("core_services", ["starting service 'vold'", "starting service `vold`"]),
    ("boot_animation", ["Service 'bootanim'", "bootanimation"]),
    ("zygote_start", ["zygote", "Zygote", "AndroidRuntime"]),
    ("preload", ["boot_progress_preload_start"]),
    ("preload_done", ["boot_progress_preload_end"]),
    ("system_server", ["boot_progress_system_run", "SystemServer",
                       "Entered the Android system server"]),
    ("package_scan", ["boot_progress_pms_start", "PackageManager"]),
    ("package_scan_done", ["boot_progress_pms_scan_done"]),
    ("package_ready", ["boot_progress_pms_ready"]),
    ("activity_manager", ["boot_progress_ams_ready"]),
    ("screen_on", ["boot_progress_enable_screen", "Display ready"]),
    ("boot_complete", ["sys.boot_completed=1", "boot_completed: 1",
                       "Boot completed", "boot_progress_last"]),
]

SLOW_THRESHOLD_S = 5.0
SLOW_MIN_SHARE = 0.10  # must also be >= 10% of the boot to be "slow"

# Lines where the system prints its own elapsed time for an action or
# service, e.g. "init: processing action (late-fs) took 1450ms".
EXPLICIT_DURATION_RE = re.compile(
    r"(?:took|duration[=:])\s*(\d+(?:\.\d+)?)\s*"
    r"(ms|msec|milliseconds|s|sec|seconds)\b",
    re.IGNORECASE,
)
ACTION_NAME_RE = re.compile(r"processing action \(([^)]+)\)")
SERVICE_NAME_RE = re.compile(r"[Ss]ervice '([^']+)'")


def _marker_hit(message: str, substrings) -> bool:
    low = message.lower()
    return any(s.lower() in low for s in substrings)


def analyze(entries: List[LogEntry],
            slow_threshold: float = SLOW_THRESHOLD_S) -> BootTiming:
    timed = [e for e in entries if e.timestamp is not None]
    timing = BootTiming(timestamps_found=bool(timed))
    if not timed:
        timing.note = ("No timestamps found in this log, so boot timing "
                       "could not be measured.")
        return timing

    timing.duration = round(timed[-1].timestamp - timed[0].timestamp, 3)

    hits = []  # (timestamp, stage_name) in log order
    seen = set()
    for entry in timed:
        for stage_name, substrings in STAGE_MARKERS:
            if stage_name in seen:
                continue
            if _marker_hit(entry.message, substrings) or _marker_hit(entry.tag, substrings):
                hits.append((entry.timestamp, stage_name))
                seen.add(stage_name)
                break

    # A stage runs from its own marker to the next observed marker.
    stages: List[BootStage] = []
    for i, (ts, name) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else timed[-1].timestamp
        stages.append(BootStage(name=name, start=ts, end=end))

    # A marker-derived stage covering (nearly) the whole log is fabricated
    # detail: the log has no intermediate markers, so no single phase can be
    # measured. Drop it rather than claim one stage took the entire boot.
    dropped_whole_boot = False
    if timing.duration and timing.duration > 0:
        kept: List[BootStage] = []
        for stage in stages:
            if stage.duration >= 0.99 * timing.duration:
                dropped_whole_boot = True
            else:
                kept.append(stage)
        stages = kept

    # Explicitly timed actions/services become stages as well, unless a
    # marker-derived stage already carries that name.
    known = {name for _, name in hits}
    labeled = set()
    for entry in timed:
        match = EXPLICIT_DURATION_RE.search(entry.message)
        if not match:
            continue
        amount = float(match.group(1))
        seconds = (amount / 1000.0
                   if match.group(2).lower() in ("ms", "msec", "milliseconds")
                   else amount)
        action = ACTION_NAME_RE.search(entry.message)
        service = SERVICE_NAME_RE.search(entry.message)
        if action:
            label = "action " + action.group(1)
        elif service:
            label = "service " + service.group(1)
        else:
            label = entry.tag or "timed action"
        if label in known or label in labeled:
            continue
        labeled.add(label)
        stages.append(BootStage(name=label,
                                start=round(entry.timestamp - seconds, 3),
                                end=entry.timestamp))
    stages.sort(key=lambda s: s.start)

    if timing.duration and timing.duration > 0:
        for stage in stages:
            if (stage.duration >= slow_threshold
                    and stage.duration >= SLOW_MIN_SHARE * timing.duration):
                stage.slow = True
                stage.note = (f"took {stage.duration:.1f}s "
                              f"({stage.duration / timing.duration:.0%} of boot)")
    timing.stages = stages
    timing.slow_stages = [s for s in stages if s.slow]
    if dropped_whole_boot:
        timing.note = ("The log spans the reported time but has no "
                       "intermediate boot markers, so per-stage timing is "
                       "unavailable; only explicitly timed actions (if any) "
                       "are listed.")
    elif not stages:
        timing.note = ("Timestamps were found but no known boot markers "
                       "(boot_progress_*, kernel milestones). Only total "
                       "elapsed time is reported.")
    return timing
