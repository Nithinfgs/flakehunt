"""Command line interface."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from . import __version__
from .analyze import BROKEN, FLAKY, TestStat, analyse
from .report import Style, render_hunt, render_why, to_json, to_markdown, want_color
from .runner import HuntError, RunRecord, hunt, is_pytest, resolve_pytest
from .why import PytestSession, display_command, explain, nodeid_to_junit, strip_positionals

EXIT_OK, EXIT_FLAKY, EXIT_ERROR = 0, 1, 2


def _split_command(argv: list[str]) -> tuple[list[str], list[str]]:
    if "--" in argv:
        i = argv.index("--")
        return argv[:i], argv[i + 1 :]
    return argv, []


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="flakehunt",
        description="Find flaky tests, then find the test that poisons them.",
    )
    p.add_argument("--version", action="version", version=f"flakehunt {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run a test command N times and report flaky tests")
    r.add_argument("-n", "--runs", type=int, default=10, help="number of runs (default 10)")
    r.add_argument("--junit", help="JUnit XML path/glob the command writes (needed unless pytest)")
    r.add_argument("--vary", action="store_true", help="set PYTHONHASHSEED=<run> each run")
    r.add_argument("--timeout", type=float, help="per-run timeout in seconds")
    r.add_argument("--cwd", type=Path, default=None, help="working directory for the command")
    r.add_argument("--json", dest="json_out", help="write machine-readable results here")
    r.add_argument("--md", dest="md_out", help="write a Markdown summary here (PR comments)")
    r.add_argument("--fail-on-flaky", action="store_true", help="exit 1 if any test is flaky")
    r.add_argument(
        "--no-isolate",
        action="store_true",
        help="skip re-running always-failing pytest tests alone",
    )
    r.add_argument("--quiet", action="store_true", help="no per-run progress on stderr")
    r.epilog = "Put the test command after --, e.g.  flakehunt run -n 20 -- pytest -q"

    w = sub.add_parser("why", help="explain one test; find what pollutes it (pytest)")
    w.add_argument("nodeid", help="pytest node id, e.g. tests/test_a.py::test_x")
    w.add_argument("-n", "--runs", type=int, default=10, help="runs per condition (default 10)")
    w.add_argument("--max-probes", type=int, default=60, help="delta-debugging budget")
    w.add_argument("--cwd", type=Path, default=None)
    w.epilog = "Optionally put your pytest command after --, e.g.  -- uv run pytest -q"

    d = sub.add_parser("demo", help="try it on a bundled project with planted flaky tests")
    d.add_argument("-n", "--runs", type=int, default=12)
    d.add_argument("--keep", type=Path, help="copy the demo project here and leave it")
    return p


def _progress(rec: RunRecord, total: int) -> None:
    failed = sum(1 for c in rec.cases if c.outcome == "fail")
    print(
        f"  run {rec.index}/{total}: {len(rec.cases)} tests, {failed} failed ({rec.duration:.1f}s)",
        file=sys.stderr,
    )


def cmd_run(args: argparse.Namespace, command: list[str]) -> int:
    style = Style(want_color())
    on_run = None if args.quiet else (lambda rec: _progress(rec, args.runs))
    records = hunt(
        command,
        runs=args.runs,
        junit=args.junit,
        vary=args.vary,
        timeout=args.timeout,
        cwd=args.cwd,
        on_run=on_run,
    )
    stats = analyse([r.cases for r in records])
    if is_pytest(command):
        _enrich_pytest(stats, command, args.cwd or Path.cwd(), isolate=not args.no_isolate)
    shown = " ".join(display_command(command))
    print(render_hunt(stats, args.runs, shown, style))
    if args.json_out:
        Path(args.json_out).write_text(to_json(stats, args.runs, shown) + "\n", encoding="utf-8")
    if args.md_out:
        Path(args.md_out).write_text(to_markdown(stats, args.runs, shown) + "\n", encoding="utf-8")
    flaky = any(s.status == FLAKY for s in stats)
    return EXIT_FLAKY if (flaky and args.fail_on_flaky) else EXIT_OK


def _enrich_pytest(stats: list[TestStat], command: list[str], cwd: Path, isolate: bool) -> None:
    """Show pytest node ids, and re-run always-failing tests alone to spot order dependence."""
    session = PytestSession(strip_positionals(command), cwd)
    try:
        order = session.collect()
    except HuntError:
        return
    by_junit = {".".join(nodeid_to_junit(n)): n for n in order}
    for st in stats:
        st.id = by_junit.get(st.id, st.id)
    if not isolate:
        return
    for st in [s for s in stats if s.status == BROKEN][:10]:
        if st.id not in order:
            continue
        try:
            st.alone = "pass" if session.outcome([st.id], st.id).outcome == "pass" else "fail"
        except HuntError:
            continue


def cmd_why(args: argparse.Namespace, command: list[str]) -> int:
    style = Style(want_color())
    pytest_cmd = command or resolve_pytest()
    cwd = args.cwd or Path.cwd()
    res = explain(
        pytest_cmd,
        args.nodeid,
        cwd=cwd,
        runs=args.runs,
        max_calls=args.max_probes,
        on_step=lambda s: print(f"  {s}...", file=sys.stderr),
    )
    print(render_why(res, style))
    return EXIT_OK


def cmd_demo(args: argparse.Namespace) -> int:
    pytest_cmd = resolve_pytest()
    src = Path(__file__).parent / "_demo"
    dest = args.keep or Path(tempfile.mkdtemp(prefix="flakehunt-demo-"))
    if args.keep and dest.exists() and any(dest.iterdir()):
        raise HuntError(f"{dest} is not empty; pick a new folder for --keep")
    try:
        shutil.copytree(
            src,
            dest,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"),
        )
        print(
            "Demo project: 28 tests with planted flakiness (see its tests/ folder)\n",
            file=sys.stderr,
        )
        style = Style(want_color())
        records = hunt(
            [*pytest_cmd, "-q"],
            runs=args.runs,
            cwd=dest,
            on_run=lambda rec: _progress(rec, args.runs),
        )
        stats = analyse([r.cases for r in records])
        _enrich_pytest(stats, pytest_cmd, dest, isolate=True)
        print()
        print(render_hunt(stats, args.runs, "pytest -q", style))
        target = "tests/test_settings.py::test_default_timeout_is_30s"
        print()
        res = explain(
            pytest_cmd,
            target,
            cwd=dest,
            runs=3,
            on_step=lambda s: print(f"  {s}...", file=sys.stderr),
        )
        print(render_why(res, style))
        if args.keep:
            print(f"\nDemo project kept at {dest}")
    finally:
        if not args.keep:
            shutil.rmtree(dest, ignore_errors=True)
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    own, command = _split_command(raw)
    args = build_parser().parse_args(own)
    try:
        if args.cmd == "run":
            return cmd_run(args, command)
        if args.cmd == "why":
            return cmd_why(args, command)
        return cmd_demo(args)
    except HuntError as exc:
        print(f"flakehunt: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except KeyboardInterrupt:
        print("\nflakehunt: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
