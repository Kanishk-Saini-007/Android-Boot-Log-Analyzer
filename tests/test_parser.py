from bootlog_analyzer.parser import parse_text


def test_parses_dmesg_with_relative_timestamps():
    entries = parse_text(
        "[    1.000000] first message\n"
        "[    3.500000] second message\n")
    assert [e.source for e in entries] == ["dmesg", "dmesg"]
    assert entries[0].timestamp == 0.0
    assert entries[1].timestamp == 2.5


def test_parses_logcat_threadtime():
    entries = parse_text(
        "10-30 09:15:00.000  1000  1000 I Zygote: Preloading classes...\n"
        "10-30 09:15:02.500  1600  1600 E ActivityManager: boom\n")
    assert entries[0].level == "INFO"
    assert entries[1].level == "ERROR"
    assert entries[1].tag == "ActivityManager"
    assert entries[1].timestamp == 2.5


def test_logcat_levels_map():
    entries = parse_text(
        "10-30 09:15:00.000  1  1 W tag: warn me\n"
        "10-30 09:15:01.000  1  1 F tag: fatal\n")
    assert entries[0].level == "WARNING"
    assert entries[1].level == "CRITICAL"


def test_unrecognised_lines_are_kept():
    entries = parse_text("this is not a log line\n")
    assert len(entries) == 1
    assert entries[0].source == "unknown"


def test_kernel_level_inference():
    entries = parse_text(
        "[    1.0] watchdog: BUG: soft lockup - CPU#2 stuck for 22s!\n"
        "[    2.0] i2c error: -107\n"
        "[    3.0] falling back to defaults\n"
        "[    4.0] all good here\n")
    assert [e.level for e in entries] == ["CRITICAL", "ERROR", "WARNING", "INFO"]
