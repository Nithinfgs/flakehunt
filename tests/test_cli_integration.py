"""End-to-end tests against the bundled demo project (real pytest subprocesses)."""

import json
import shutil
import sys
from pathlib import Path

import pytest

import flakehunt
from flakehunt.cli import main
from flakehunt.why import nodeid_to_junit


@pytest.fixture()
def demo(tmp_path: Path) -> Path:
    dest = tmp_path / "demo"
    src = Path(flakehunt.__file__).parent / "_demo"
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__"))
    return dest


PYTEST = [sys.executable, "-m", "pytest", "-q"]


def test_run_finds_planted_flakes(demo, tmp_path, capsys):
    out_json = tmp_path / "r.json"
    out_md = tmp_path / "r.md"
    code = main(
        [
            "run",
            "-n",
            "12",
            "--cwd",
            str(demo),
            "--quiet",
            "--json",
            str(out_json),
            "--md",
            str(out_md),
            "--fail-on-flaky",
            "--",
            *PYTEST,
        ]
    )
    assert code == 1
    data = json.loads(out_json.read_text())
    status = {t["id"]: t for t in data["tests"]}
    assert status["tests/test_sync.py::test_websocket_reconnects"]["status"] == "flaky"
    assert status["tests/test_sync.py::test_cache_warms_before_deadline"]["status"] == "flaky"
    assert status["tests/test_legacy.py::test_2019_tax_table"]["passes_alone"] is False
    polluted = status["tests/test_settings.py::test_default_timeout_is_30s"]
    assert polluted["status"] == "broken" and polluted["passes_alone"] is True
    assert data["summary"]["flaky"] == 2
    assert "test_websocket_reconnects" in out_md.read_text()
    assert "flaky" in capsys.readouterr().out.lower()


def test_run_exit_zero_without_flag(demo, capsys):
    code = main(["run", "-n", "3", "--cwd", str(demo), "--quiet", "--", *PYTEST])
    assert code == 0


def test_why_finds_minimal_polluter(demo, capsys):
    code = main(
        [
            "why",
            "tests/test_settings.py::test_default_timeout_is_30s",
            "-n",
            "2",
            "--cwd",
            str(demo),
            "--",
            *PYTEST,
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "order-dependent" in out
    assert "tests/test_checkout.py::test_slow_network_profile" in out


def test_why_reports_intrinsic_flake(demo, capsys):
    # With FLAKEHUNT_RUN set per probe, test_websocket_reconnects fails alone on some runs.
    main(
        [
            "why",
            "tests/test_sync.py::test_websocket_reconnects",
            "-n",
            "12",
            "--cwd",
            str(demo),
            "--",
            *PYTEST,
        ]
    )
    assert "intrinsically flaky" in capsys.readouterr().out


def test_why_unknown_node_id(demo, capsys):
    code = main(["why", "tests/test_nope.py::test_x", "--cwd", str(demo), "--", *PYTEST])
    assert code == 2
    assert "not collected" in capsys.readouterr().err


def test_non_pytest_requires_junit(capsys):
    code = main(["run", "-n", "2", "--", sys.executable, "-c", "pass"])
    assert code == 2
    assert "--junit" in capsys.readouterr().err


def test_generic_runner_with_junit_file(tmp_path, capsys):
    script = tmp_path / "fake_runner.py"
    script.write_text(
        "import os, pathlib\n"
        "run = int(os.environ['FLAKEHUNT_RUN'])\n"
        "fail = '<failure message=\"Connection refused\"/>' if run % 2 else ''\n"
        "pathlib.Path('out.xml').write_text("
        '\'<testsuite><testcase classname="x" name="t">%s</testcase></testsuite>\' % fail)\n'
    )
    code = main(
        [
            "run",
            "-n",
            "4",
            "--junit",
            "out.xml",
            "--cwd",
            str(tmp_path),
            "--quiet",
            "--fail-on-flaky",
            "--",
            sys.executable,
            str(script),
        ]
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "x.t" in out and "2/4 failed" in out


def test_missing_junit_is_reported(tmp_path, capsys):
    code = main(
        [
            "run",
            "-n",
            "2",
            "--junit",
            "never.xml",
            "--cwd",
            str(tmp_path),
            "--",
            sys.executable,
            "-c",
            "pass",
        ]
    )
    assert code == 2
    assert "no JUnit results" in capsys.readouterr().err


def test_nodeid_to_junit():
    assert nodeid_to_junit("tests/test_a.py::Cls::test_x[p-1]") == (
        "tests.test_a.Cls",
        "test_x[p-1]",
    )
    assert nodeid_to_junit("a.py::t") == ("a", "t")


def test_demo_command_end_to_end(capsys, tmp_path):
    keep = tmp_path / "kept"
    code = main(["demo", "-n", "6", "--keep", str(keep)])
    out = capsys.readouterr().out
    assert code == 0
    assert "FLAKY" in out and "Minimal polluter" in out
    assert (keep / "tests" / "test_settings.py").exists()


@pytest.mark.parametrize(
    "argv,expected",
    [
        (["pytest", "-q"], True),
        (["C:\\Python\\Scripts\\pytest.EXE", "-q"], True),
        (["/usr/bin/python3", "-m", "pytest"], True),
        (["py.test"], True),
        (["npx", "jest"], False),
        (["python", "-m", "unittest"], False),
    ],
)
def test_is_pytest(argv, expected):
    from flakehunt.runner import is_pytest

    assert is_pytest(argv) is expected
