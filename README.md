# Android Boot Log Analyzer

A Python tool that reads Android boot logs (`dmesg` and `logcat`), finds the
errors that matter, explains why a device might be booting slowly or failing
to boot, and generates a diagnostic report in HTML and JSON.

Built by [Kanishk Saini](https://github.com/Kanishk-Saini-007) as a learning
project. Everything in this repo is rule-based and explainable - every number
in the report can be traced back to a line in the log.

## Try it in your browser

The analyzer also runs as a web page - no install, and your logs are never
uploaded anywhere:
**<https://kanishk-saini-007.github.io/Android-Boot-Log-Analyzer/>**

Paste or load your own `dmesg`/`logcat` output, analyze it, and download the
same HTML/JSON reports the CLI writes. The page (`docs/index.html`, served
with GitHub Pages) is a JavaScript port of this exact package. The bundled
sample logs are synthetic, and are labeled as such on the page.

## The problem

Android developers deal with thousands of boot-log lines. Manually finding
kernel errors, driver failures, missing firmware and slow startup services
takes time. This tool automates that analysis and produces a report you can
read in seconds.

## Features

The five core pieces:

1. **Log Reader** - parses `dmesg` and logcat (`threadtime` and `brief`
   formats), auto-detected per line.
2. **Error Detector** - finds `ERROR`, `WARNING` and `CRITICAL` messages,
   and promotes patterns that are never benign during boot (SELinux denials,
   explicit "failed"/"error" wording).
3. **Error Classifier** - categorizes issues as **kernel**, **driver**,
   **firmware** or **SELinux**, with a concrete recommendation for each
   category. Anything that matches no rule is reported as **other** so no
   detected issue is silently dropped.
4. **Boot Time Analyzer** - measures every boot stage from the log's own
   timestamps (kernel, init, zygote, package scan, activity manager, screen
   on, boot complete) and flags slow stages.
5. **Report Generator** - writes a self-contained **HTML** report and a
   machine-readable **JSON** report.

## Quickstart

Requires Python 3.10+. No runtime dependencies - the analyzer is pure
standard library.

```bash
git clone https://github.com/Kanishk-Saini-007/android-boot-log-analyzer.git
cd android-boot-log-analyzer

# Analyze a log (writes report.html and report.json)
python3 -m bootlog_analyzer sample_logs/boot_failure.log

# Choose output paths
python3 -m bootlog_analyzer analyze sample_logs/boot_slow.log \
    --json reports/my_report.json --html reports/my_report.html
```

## Collecting real logs with ADB

```bash
# Kernel log (needs root or a debug build on many devices)
adb shell dmesg > my_boot_dmesg.log

# Full userspace log right after boot
adb logcat -b all -d -v threadtime > my_boot_logcat.log
```

Both files can be fed straight to the analyzer.

## Example output

Running on `sample_logs/boot_failure.log` (a synthetic log included in this
repo):

```text
Boot Diagnostic Report
========================================
7 issue(s) detected
* Total boot time: 42.0 seconds
* Kernel issue: 1
* Driver issues: 4
* Firmware issue: 1
* SELinux issue: 1

Slow boot stages:
* selinux_setup: 9.9s
* core_services: 29.7s

Recommendations
* Check firmware availability: confirm the firmware file exists under
  /vendor/firmware or /lib/firmware and matches the driver version.
* Investigate driver initialization failure: check the device tree,
  power/clock configuration and probe order for this peripheral.
* Investigate the kernel error: check recent kernel, config or hardware
  changes and capture a full dmesg around the failure.
* Review SELinux permission rules: audit the denial and update sepolicy
  instead of disabling enforcement.
```

The HTML version of the same report shows the summary cards, boot-stage
table, issue cards and recommendations. See [`reports/`](reports/) for
generated HTML and JSON reports for every sample log.

## Sample logs

The files in [`sample_logs/`](sample_logs/) are **synthetic** - written by
hand to contain known failures so the rules can be tested. They are
illustrative, not measurements of a real device.

| File | Format | What it demonstrates |
| --- | --- | --- |
| `boot_failure.log` | dmesg | Firmware load failure, driver probe errors, SELinux denial, CPU soft lockup |
| `boot_fixed.log` | dmesg | The same boot after the fixes - a clean kernel log |
| `boot_slow.log` | logcat | 42s boot with a 14.5s package scan and other slow stages |
| `boot_healthy.log` | logcat | Clean 9s boot with no detected issues |

## Real emulator logs

The files in [`sample_logs/real_emulator/`](sample_logs/real_emulator/) are
**real boot logs**, collected from an Android emulator running in GitHub
Actions - not from a physical phone, and not written by hand.

How they were collected (2 November 2026, UTC):

- Emulator: `sdk_gphone64_x86_64`, Android 15 (API 35), `google_apis`
  x86_64 system image, Pixel 7 Pro profile, booted with
  [android-emulator-runner](https://github.com/ReactiveCircus/android-emulator-runner)
- Commands, run right after boot finished:
  `adb shell dmesg > real_boot_dmesg.log` and
  `adb logcat -b all -d -v threadtime > real_boot_logcat.log`
- The workflow in
  [`.github/workflows/real-boot-logs.yml`](.github/workflows/real-boot-logs.yml)
  boots the emulator, saves the logs, runs the analyzer on them and commits
  the results. Before committing it scans both logs for identifier-looking
  strings (MAC addresses, emails, IMEI/serial/password-like text) and
  refuses to commit if anything unreviewed appears.

The matching analyzer reports are
[`reports/real_logcat_report.html`](reports/real_logcat_report.html) /
[`.json`](reports/real_logcat_report.json) and
[`reports/real_dmesg_report.html`](reports/real_dmesg_report.html) /
[`.json`](reports/real_dmesg_report.json).
A fresh emulator's first boot logs a lot of expected noise (first-time
service starts, dex2oat compiling apps), so the issue counts are higher
than on a settled device.

## How it works

The analyzer mirrors the real Android boot sequence
**Bootloader -> Kernel -> Init -> Android Framework**:

1. `parser.py` turns each raw line into a structured entry (timestamp,
   level, tag, message) and normalizes timestamps so the first timestamped
   line is `t=0`. Kernel messages carry no level, so one is inferred from
   the wording ("BUG", "failed", "deprecated", ...).
2. `detector.py` keeps the entries worth a human's attention and suppresses
   a small list of known-noise patterns.
3. `classifier.py` applies ordered keyword rules (most specific first) to
   assign a category and a recommendation. The rules are plain Python -
   read them, extend them.
4. `boot_time.py` looks for the standard markers Android emits while
   booting (`boot_progress_*`, `sys.boot_completed=1`, kernel milestones).
   A stage's duration is simply the distance to the next marker, and a
   stage is slow when it takes 5+ seconds and at least 10% of the boot.
5. `report.py` renders the JSON report and the single-file HTML report
   (inline CSS, no JavaScript, no network).

## Project structure

```text
bootlog_analyzer/
  parser.py       # log reader: dmesg + logcat -> structured entries
  detector.py     # error detector: ERROR / WARNING / CRITICAL
  classifier.py   # error classifier: kernel, driver, firmware, selinux
  boot_time.py    # boot time analyzer: stage durations, slow stages
  report.py       # HTML + JSON report generation
  cli.py          # command line interface
sample_logs/      # synthetic logs with known failures (see table above)
  real_emulator/  # real logs collected via ADB from a CI emulator
reports/          # generated sample reports (HTML + JSON)
tests/            # 25 pytest tests covering every module
```

## Running the tests

```bash
pip install -r requirements-dev.txt
python3 -m pytest -q
```

Tests run against logs containing known errors, so a passing suite means
the rules actually catch what they claim to catch. CI runs the same suite
on every push.

## What I learned building this

- Reading and processing text files in Python, line by line
- Regular expressions to extract errors, levels and timestamps
- The Android boot process: Bootloader -> Kernel -> Init -> Framework
- Collecting logs over ADB (`dmesg`, `logcat`)
- Writing rule-based diagnostics that stay explainable
- Testing with pytest against fixtures containing known errors

## Limitations (honest ones)

- Detection is keyword/rule-based. It catches common boot failures but it
  is not a substitute for reading the log yourself on a hard bug.
- Boot stage timing needs the standard markers; vendor logs that strip
  them still get total-elapsed timing but no per-stage breakdown.
- The four logs in `sample_logs/` are synthetic; the real emulator logs
  in `sample_logs/real_emulator/` are from a first boot of a stock
  emulator image, which is noisier than a real daily-use device.

## Learning resources

| Topic | Resource |
| --- | --- |
| Python basics | [W3Schools](https://www.w3schools.com/python/) |
| Regular expressions | [RegexOne](https://regexone.com/) |
| Linux commands | [Linux Journey](https://linuxjourney.com/) |
| Android boot process | [Android documentation](https://source.android.com/docs/core/architecture/bootloader) |
| ADB | [ADB documentation](https://developer.android.com/tools/adb) |
| Python testing | [pytest](https://docs.pytest.org/) |

## License

MIT - see [LICENSE](LICENSE).
