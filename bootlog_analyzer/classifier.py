"""Error classifier: assigns each issue to a failure category.

The rules are plain keyword matching, ordered from most specific to most
general. Every rule is documented and easy to extend - that is deliberate:
this tool is a learning project, not a black box.
"""
from __future__ import annotations

from .models import Issue, LogEntry

# (category, keywords, recommendation). First matching rule wins.
RULES = [
    (
        "selinux",
        ["avc:", "selinux", "denied", "sepolicy", "permissive="],
        "Review SELinux permission rules: audit the denial and update sepolicy "
        "instead of disabling enforcement.",
    ),
    (
        "firmware",
        ["firmware", "fw load", ".bin", ".tlv", ".fw", "direct firmware load"],
        "Check firmware availability: confirm the firmware file exists under "
        "/vendor/firmware or /lib/firmware and matches the driver version.",
    ),
    (
        "driver",
        [
            "driver", "probe", "i2c", "spi", "usb", "regulator", "wlan",
            "wifi", "bluetooth", "bt_", "camera", "sensor", "audio", "gpu",
            "drm", "mmc", "sdhci", "uart", "touchscreen", "charger",
        ],
        "Investigate driver initialization failure: check the device tree, "
        "power/clock configuration and probe order for this peripheral.",
    ),
    (
        "kernel",
        [
            "kernel", "panic", "oops", "bug:", "call trace", "lockup",
            "mount root", "initramfs", "page allocation", "oom",
        ],
        "Investigate the kernel error: check recent kernel, config or "
        "hardware changes and capture a full dmesg around the failure.",
    ),
]

DEFAULT_RECOMMENDATION = (
    "Review the log context around this line for the root cause."
)

CATEGORY_LABELS = {
    "kernel": "Kernel",
    "driver": "Driver",
    "firmware": "Firmware",
    "selinux": "SELinux",
    "other": "Other",
}


def classify(entry: LogEntry) -> tuple:
    """Return (category, recommendation) for a log entry."""
    haystack = (entry.tag + " " + entry.message).lower()
    for category, keywords, recommendation in RULES:
        if any(kw in haystack for kw in keywords):
            return category, recommendation
    # Kernel log lines that matched nothing else are still kernel territory.
    if entry.source == "dmesg":
        for category, keywords, recommendation in RULES:
            if category == "kernel":
                return category, recommendation
    return "other", DEFAULT_RECOMMENDATION
