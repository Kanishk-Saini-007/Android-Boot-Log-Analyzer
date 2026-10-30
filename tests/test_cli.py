from pathlib import Path

from bootlog_analyzer.cli import main

SAMPLES = Path(__file__).resolve().parent.parent / "sample_logs"


def test_analyze_writes_both_reports(tmp_path, capsys):
    json_out = tmp_path / "r.json"
    html_out = tmp_path / "r.html"
    rc = main(["analyze", str(SAMPLES / "boot_failure.log"),
               "--json", str(json_out), "--html", str(html_out)])
    assert rc == 0
    assert json_out.exists() and html_out.exists()
    out = capsys.readouterr().out
    assert "Boot Diagnostic Report" in out
    assert "Recommendations" in out


def test_bare_filename_defaults_to_analyze(tmp_path):
    rc = main([str(SAMPLES / "boot_healthy.log")])
    assert rc == 0
    assert (Path.cwd() / "report.json").exists()
    (Path.cwd() / "report.json").unlink()
    (Path.cwd() / "report.html").unlink()


def test_missing_file_returns_1(capsys):
    rc = main(["analyze", "no_such_file.log", "--json", "", "--html", ""])
    assert rc == 1
    assert "error" in capsys.readouterr().err


def test_compare_mode(capsys):
    rc = main(["compare", str(SAMPLES / "boot_failure.log"),
               str(SAMPLES / "boot_fixed.log")])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Fixed issues" in out
    assert "New issues" in out
