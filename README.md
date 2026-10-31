# Android Boot Log Analyzer

A Python tool that reads Android boot logs (`dmesg` and `logcat`), finds the
errors that matter, explains why a device might be booting slowly or failing
to boot, and generates a diagnostic report in HTML and JSON.

Built by [Kanishk Saini](https://github.com/KanishkSaini-007) as a learning
project. Everything in this repo is rule-based and explainable - every number
in the report can be traced back to a line in the log.

## Try it in your browser

The whole analyzer also runs as a web page - no install, and your logs are
never uploaded anywhere:
**<https://kanishksaini-007.github.io/android-boot-log-analyzer/>**

Paste or load your own `dmesg`/`logcat` output, analyze it, compare two
boots, and download the same HTML/JSON reports the CLI writes. The page
(`docs/index.html`, served with GitHub Pages) is a JavaScript port of this
exact package, with its output checked against the CLI. The bundled sample
logs are synthetic, and are labeled as such on the page.

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
   **firmware**, **SELinux**, **system** or **other**, with a concrete
   recommendation for each category.
4. **Boot Time Analyzer** - measures every boot stage from the log's own
   timestamps (kernel, init, zygote, package scan, activity manager, screen
   on, boot complete) and flags slow stages.
5. **Report Generator** - writes a self-contained **HTML** report and a
   machine-readable **JSON** report.

Three extras on top:

- **Boot timeline** - the HTML report draws an SVG timeline: stages as bars
  (slow ones in red) and issues as dots at the exact moment they fired. One
  glance shows where the boot spent its time and where failures clustered.
- **Boot Health Score (0-100)** - a transparent grade with the exact math
  printed next to it (`100 - 25 per CRITICAL - 10 per ERROR - 3 per WARNING
  - 5 per slow stage`). No black box.
- **Compare mode** - diff two boot logs to see which issues are new, which
  are fixed, and whether the boot got faster or slower. The question every
  developer asks after a change.

## Quickstart

Requires Python 3.10+. No runtime dependencies - the analyzer is pure
standard library.

```bash
git clone https://github.com/KanishkSaini-007/android-boot-log-analyzer.git
cd android-boot-log-analyzer

# Analyze a log (writes report.html and report.json)
python3 -m bootlog_analyzer sample_logs/boot_failure.log

# Choose output paths
python3 -m bootlog_analyzer analyze sample_logs/boot_slow.log \
    --json reports/my_report.json --html reports/my_report.html

# Compare two boots (before/after a change)
python3 -m bootlog_analyzer compare sample_logs/boot_failure.log \
    sample_logs/boot_fixed.log
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
* Boot Health Score: 5/100 (Critical)

Slow boot stages:
* selinux setup: 9.9s
* core services: 29.7s

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

The HTML version of the same report shows the boot timeline, stage table,
issue cards and recommendations. See [`reports/`](reports/) for generated
HTML and JSON reports for every sample log, plus a compare-mode example
(`compare_failure_vs_fixed.json`).

## Sample logs

The files in [`sample_logs/`](sample_logs/) are **synthetic** - written by
hand to contain known failures so the rules can be tested. They are
illustrative, not measurements of a real device.

| File | Format | What it demonstrates |
| --- | --- | --- |
| `boot_failure.log` | dmesg | Firmware load failure, driver probe errors, SELinux denial, CPU soft lockup |
| `boot_fixed.log` | dmesg | The same boot after the fixes - use with `compare` |
| `boot_slow.log` | logcat | 42s boot with a 14.5s package scan and other slow stages |
| `boot_healthy.log` | logcat | Clean 9s boot, health score 100 |

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
5. `score.py` computes the Boot Health Score. The formula is five lines and
   printed in full in every report.
6. `report.py` renders the JSON report and the single-file HTML report
   (inline CSS + SVG, no JavaScript, no network).

## Project structure

```text
bootlog_analyzer/
  parser.py       # log reader: dmesg + logcat -> structured entries
  detector.py     # error detector: ERROR / WARNING / CRITICAL
  classifier.py   # error classifier: kernel, driver, firmware, selinux, ...
  boot_time.py    # boot time analyzer: stage durations, slow stages
  score.py        # boot health score (0-100, fully explained)
  compare.py      # compare two boots: new/fixed issues, verdict
  report.py       # HTML + JSON report generation
  cli.py          # command line interface
sample_logs/      # synthetic logs with known failures (see table above)
reports/          # generated sample reports (HTML + JSON)
tests/            # 30 pytest tests covering every module
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
- The sample logs are synthetic. Real logs from your own device or the
  emulator are the best test - pull them with ADB and run the tool.

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
