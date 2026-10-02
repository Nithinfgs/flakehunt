"""Run a test command repeatedly and collect JUnit results from each run."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .junit import Case, parse_junit


class HuntError(Exception):
    """A user-facing failure (bad command, no JUnit output, ...)."""


@dataclass
class RunRecord:
    index: int  # 1-based
    returncode: int
    duration: float
    cases: list[Case]
    log_tail: str = ""


def is_pytest(argv: list[str]) -> bool:
    names = [re.split(r"[\\/]", a)[-1].lower().removesuffix(".exe") for a in argv[:4]]
    if "pytest" in names or "py.test" in names:
        return True
    return "-m" in argv and "pytest" in argv[argv.index("-m") + 1 : argv.index("-m") + 2]


def resolve_pytest() -> list[str]:
    """Locate a pytest invocation: the executable on PATH, else this interpreter's module."""
    exe = shutil.which("pytest")
    if exe:
        return [exe]
    try:
        import importlib.util

        if importlib.util.find_spec("pytest"):
            import sys

            return [sys.executable, "-m", "pytest"]
    except (ImportError, ValueError):
        pass
    raise HuntError("pytest not found. Install it, or run via: uvx --with pytest flakehunt ...")


def run_once(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: float | None,
) -> tuple[int, float, str]:
    start = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise HuntError(f"command not found: {argv[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout if isinstance(exc.stdout, str) else ""
        return 124, time.monotonic() - start, out[-2000:] + "\n[flakehunt: run timed out]"
    return proc.returncode, time.monotonic() - start, proc.stdout[-2000:]


def hunt(
    argv: list[str],
    *,
    runs: int,
    junit: str | None = None,
    vary: bool = False,
    timeout: float | None = None,
    cwd: Path | None = None,
    on_run: Callable[[RunRecord], None] | None = None,
) -> list[RunRecord]:
    """Execute ``argv`` ``runs`` times and parse the JUnit XML each run produces.

    For pytest, the XML path is injected automatically. For any other runner the command
    must write XML itself and ``junit`` must point at it (a path or glob, relative to cwd).
    """
    if runs < 2:
        raise HuntError("need at least 2 runs to detect flakiness")
    if not argv:
        raise HuntError("no test command given (put it after `--`)")
    cwd = cwd or Path.cwd()
    tmp = Path(tempfile.mkdtemp(prefix="flakehunt-"))
    try:
        if junit is None:
            if not is_pytest(argv):
                raise HuntError(
                    "only pytest is auto-detected; for other runners pass --junit PATH "
                    "pointing at the XML your command writes"
                )
            xml_path = str(tmp / "junit.xml")
            command = [*argv, f"--junitxml={xml_path}"]
        else:
            xml_path = junit if os.path.isabs(junit) else str(cwd / junit)
            command = list(argv)
        records: list[RunRecord] = []
        for i in range(1, runs + 1):
            for stale in Path(xml_path).parent.glob(Path(xml_path).name):
                stale.unlink(missing_ok=True)
            env = dict(os.environ)
            env["FLAKEHUNT_RUN"] = str(i)
            if vary:
                env["PYTHONHASHSEED"] = str(i)
            code, dur, tail = run_once(command, cwd=cwd, env=env, timeout=timeout)
            cases = parse_junit(xml_path)
            if not cases:
                raise HuntError(
                    f"run {i} produced no JUnit results at {xml_path} "
                    f"(exit code {code}). Last output:\n{tail.strip()}"
                )
            rec = RunRecord(i, code, dur, cases, tail)
            records.append(rec)
            if on_run:
                on_run(rec)
        return records
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
