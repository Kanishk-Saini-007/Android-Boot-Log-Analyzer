from bootlog_analyzer.classifier import classify
from bootlog_analyzer.parser import parse_text


def _cat(line):
    return classify(parse_text(line)[0])[0]


def test_firmware_wins_over_driver_keywords():
    assert _cat("[    6.0] qca_cld3_wlan: Direct firmware load for "
                "wlan/fw.bin failed with error -2") == "firmware"


def test_selinux_detection():
    assert _cat("[   33.0] avc:  denied  { read } for pid=512 comm=\"vold\"") \
        == "selinux"


def test_driver_detection():
    assert _cat("[    7.8] i2c_geni 4a90000.i2c: i2c error: -107") == "driver"


def test_kernel_default_for_dmesg():
    assert _cat("[   28.4] watchdog: BUG: soft lockup - CPU#2 stuck!") \
        == "kernel"


def test_unknown_falls_back_to_other_for_logcat():
    assert _cat("10-30 09:15:00.000  1  1 E mystery: unrecognised thing") \
        == "other"
