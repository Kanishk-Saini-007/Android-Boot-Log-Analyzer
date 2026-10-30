"""Boot time analyzer: measures how long each boot stage took.

Android emits well-known markers while booting. From logcat we read the
``boot_progress_*`` events and the ``sys.boot_completed=1`` property; from
dmesg we read kernel milestones. Every stage duration is the time between
two consecutive observed markers, so the numbers are explainable from the
log itself - nothing is estimated.

A stage is flagged slow when it takes longer than ``slow_threshold``
seconds (default 5s) and accounts for at least 10% of the boot.
"""
from __future__ import annotations

from typing import List, Optional

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

    if timing.duration and timing.duration > 0:
        for stage in stages:
            if (stage.duration >= slow_threshold
                    and stage.duration >= SLOW_MIN_SHARE * timing.duration):
                stage.slow = True
                stage.note = (f"took {stage.duration:.1f}s "
                              f"({stage.duration / timing.duration:.0%} of boot)")
    timing.stages = stages
    timing.slow_stages = [s for s in stages if s.slow]
    if not stages:
        timing.note = ("Timestamps were found but no known boot markers "
                       "(boot_progress_*, kernel milestones). Only total "
                       "elapsed time is reported.")
    return timing
