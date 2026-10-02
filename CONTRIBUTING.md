# Contributing

Thanks for helping. flakehunt is small on purpose: standard library only, offline, deterministic.

## Setup

```bash
git clone https://github.com/Nithinfgs/flakehunt && cd flakehunt
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
```

## Before opening a PR

```bash
ruff check . && ruff format --check src tests scripts
mypy
pytest
```

`tests/test_cli_integration.py` runs real pytest subprocesses against the bundled demo
project (`src/flakehunt/_demo`), so changes to run/why behaviour are covered end to end.

## Good first contributions

- A **runner recipe** that you have actually run (jest, vitest, go, cargo-nextest, rspec,
  maven): add the command line to the README table and a fixture-based test in `tests/`.
- New **cause hints** in `analyze.py` (`HINTS`). Include a real failure message as a test.
- `why` support for another runner. The seam is `PytestSession` in `why.py`: it needs
  collection (ordered ids) and "run these ids in this order, tell me the outcome of one".

## Principles

- No network calls, no telemetry, no required dependencies.
- Hints are suggestions. Never present a heuristic as a diagnosis.
- Claims in the README must be reproducible from the repository.

Use the commit style `type: summary` (`feat`, `fix`, `docs`, `test`, `ci`, `chore`).
