import pytest

from bootlog_analyzer.boot_time import analyze
from bootlog_analyzer.parser import parse_text


def test_measures_total_duration():
    entries = parse_text(
        "[    0.0] boot: Linux version x\n"
        "[   10.0] init: processing action (sys.boot_completed=1)\n")
    timing = analyze(entries)
    assert timing.duration == 10.0
    assert timing.timestamps_found


def test_flags_slow_stage():
    entries = parse_text(
        "10-30 09:15:00.000  1  1 I PackageManager: boot_progress_pms_start\n"
        "10-30 09:15:14.000  1  1 I PackageManager: boot_progress_pms_scan_done\n"
        "10-30 09:15:20.000  1  1 I sys.boot_completed: sys.boot_completed=1\n")
    timing = analyze(entries)
    slow_names = [s.name for s in timing.slow_stages]
    assert "package_scan" in slow_names


def test_no_timestamps_is_handled():
    entries = parse_text("just some text\nmore text\n")
    timing = analyze(entries)
    assert timing.duration is None
    assert "No timestamps" in timing.note


def test_missing_markers_still_reports_elapsed():
    entries = parse_text("[    1.0] hello\n[    4.0] world\n")
    timing = analyze(entries)
    assert timing.duration == 3.0
    assert timing.stages == []


def test_explicit_duration_line_becomes_stage():
    entries = parse_text(
        "[    0.0] boot: Linux version x\n"
        "[    3.0] init: processing action (late-fs) took 1450ms\n"
        "[   42.0] init: processing action (sys.boot_completed=1)\n")
    timing = analyze(entries)
    stage = next(s for s in timing.stages if s.name == "action late-fs")
    assert stage.duration == 1.45
    assert not stage.slow  # 1.45s of a 42s boot is not slow


def test_explicit_duration_can_be_flagged_slow():
    entries = parse_text(
        "[    0.0] boot: Linux version x\n"
        "[   30.0] init: processing action (late-fs) took 12000ms\n"
        "[   42.0] init: processing action (sys.boot_completed=1)\n")
    timing = analyze(entries)
    stage = next(s for s in timing.stages if s.name == "action late-fs")
    assert stage.slow
    assert stage.duration == 12.0


def test_explicit_service_duration_is_captured():
    entries = parse_text(
        "[    0.0] boot: Linux version x\n"
        "[    9.5] init: Service 'wificond' took 2.5s\n"
        "[   42.0] Boot completed\n")
    timing = analyze(entries)
    stage = next(s for s in timing.stages if s.name == "service wificond")
    assert stage.duration == 2.5


def test_sparse_log_does_not_fabricate_whole_boot_stage():
    entries = parse_text(
        "[    0.0] boot: Linux version x\n"
        "[   42.0] Boot completed\n")
    timing = analyze(entries)
    assert not any(s.slow and s.duration >= 0.9 * timing.duration
                   for s in timing.stages)
    assert "no intermediate boot markers" in timing.note
