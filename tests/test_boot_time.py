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
