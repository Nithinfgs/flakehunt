<h1 align="center">flakehunt</h1>

<p align="center"><b>Find your flaky tests, then find the test that poisons them.</b><br>
Runs your test command N times, reports what flips, and uses delta debugging to name the earlier test that breaks a victim. Offline. No dependencies. No AI.</p>

<p align="center">
  <a href="https://github.com/Nithinfgs/flakehunt/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/Nithinfgs/flakehunt/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-blue">
  <img alt="Zero dependencies" src="https://img.shields.io/badge/dependencies-0-brightgreen">
  <a href="LICENSE"><img alt="MIT" src="https://img.shields.io/badge/license-MIT-lightgrey"></a>
</p>

<p align="center"><img src="docs/assets/demo.svg" alt="flakehunt demo: two flaky tests found, one always-failing test that passes alone" width="860"></p>

## The 20-second version

A test that sometimes fails is expensive in a way retries hide: people stop trusting red. There are two very different causes, and they need different fixes:

1. **The test is nondeterministic** (timing, ports, randomness, a service that is not ready). It fails even when run by itself.
2. **The test is a victim.** It passes alone and fails only after some *other* test left state behind. In a fixed-order suite this looks like a permanent failure, not a flake, so nobody suspects order.

`flakehunt run` separates these for you. `flakehunt why` goes after the second kind: it bisects the tests that ran before the victim and returns the **minimal set that makes it fail**, plus a one-line command to reproduce.

<p align="center"><img src="docs/assets/why.svg" alt="flakehunt why pinpoints tests/test_checkout.py::test_slow_network_profile as the polluter in 7 probes" width="860"></p>

## Quick start

Needs Python 3.9+ and, for the demo, pytest. Nothing is published to PyPI yet, so install from GitHub:

```bash
# try it with zero setup: a bundled project with planted flakiness (~10 s)
uvx --with pytest --from git+https://github.com/Nithinfgs/flakehunt flakehunt demo

# or install it
pipx install git+https://github.com/Nithinfgs/flakehunt
```

Then, in your own project:

```bash
flakehunt run -n 20 -- pytest -q          # hunt: repeat the suite 20 times
flakehunt why tests/test_a.py::test_x     # explain one test, find its polluter
```

## Use it on your suite

```text
flakehunt run [-n 10] [--junit PATH] [--vary] [--timeout S] [--cwd DIR]
              [--json FILE] [--md FILE] [--fail-on-flaky] [--no-isolate] -- <test command>
flakehunt why <pytest-node-id> [-n 10] [--max-probes 60] [-- <pytest command>]
flakehunt demo [-n 12] [--keep DIR]
```

- **pytest** is auto-detected and the JUnit path is injected for you.
- **Any other runner**: make it write JUnit XML and point `--junit` at it (a path or glob, relative to `--cwd`).

| Runner | Command (JUnit output configured by the runner) |
|---|---|
| pytest | `flakehunt run -n 20 -- pytest -q` |
| jest | `flakehunt run --junit junit.xml -- npx jest --reporters=jest-junit` |
| Go | `flakehunt run --junit out.xml -- gotestsum --junitfile out.xml ./...` |
| Rust | `flakehunt run --junit "target/nextest/ci/junit.xml" -- cargo nextest run --profile ci` (JUnit enabled in `.config/nextest.toml`) |

> Only the pytest row is exercised in this repo's CI (plus a synthetic JUnit-writing runner). The other rows are standard invocations of those tools, not yet verified here. Corrections and recipes welcome: see [CONTRIBUTING](CONTRIBUTING.md).

Every run exports `FLAKEHUNT_RUN` (1, 2, 3, …) so a test can seed itself from it when you want a reproducible repro. `--vary` also sets `PYTHONHASHSEED` per run, which flushes out set/dict-ordering assumptions.

### In CI

```yaml
- run: pipx install git+https://github.com/Nithinfgs/flakehunt
- run: flakehunt run -n 10 --md flake.md --json flake.json --fail-on-flaky -- pytest -q
- if: always()
  run: cat flake.md >> "$GITHUB_STEP_SUMMARY"
```

Exit codes: `0` ok, `1` flaky tests found with `--fail-on-flaky`, `2` usage/runtime error.

## What you get

- **Flaky vs broken vs victim.** Per-test pass/fail counts, a per-run strip (`✗··✗·`), and automatic isolation of always-failing pytest tests so "broken" and "order-dependent" are not confused.
- **Failure fingerprints.** Messages are normalised (addresses, temp paths, numbers, UUIDs) so "same failure, different noise" counts as one.
- **Suspected cause.** A short list of regex heuristics (ports, readiness, timing, shared DB/files, async teardown, external services, wall-clock, randomness) with a one-line suggestion. These are hints, labelled as such.
- **Minimal polluter search.** Zeller's `ddmin` over the tests that ran before the victim, with a probe budget and per-probe retries to cope with probabilistic pollution.
- **Honest statistics.** The report prints the odds that a flaky test of a given rate would be caught in N runs. 10 runs find a 10%-flaky test only about 65% of the time; flakehunt says so instead of claiming "no flakes".
- **JSON and Markdown output** for dashboards and PR comments.

## How it works

```
 your command ×N ──► JUnit XML per run ──► per-test outcome matrix ──► classify + fingerprint + hint
                                                    │
                                   always-failing?  └─► re-run alone (pytest) ─► "passes alone" ─► why
 why <victim>:  alone ×N ──► fails? ── yes ─► intrinsic flake
                              │ no
                  earlier tests + victim ×N ─► fails? ─ no ─► not reproduced (raise -n)
                              │ yes
                         ddmin(earlier tests) ─► minimal polluter set + reproduce command
```

All process control goes through `subprocess` with your own command, your own environment and your own working directory. Collection and ordering for `why` use `pytest --collect-only`; each probe runs the explicit node-id list in order.

## Limitations

- `why`, node-id display and always-failing isolation are **pytest only** for now. Detection (`run`) works with anything that emits JUnit XML.
- `why` assumes pollution comes from tests that ran *earlier in collection order in the same process*. It does not model pytest-xdist scheduling, session-scoped state shared across processes, or external state that persists between runs (databases, files), though a stateful external polluter will still be found if it runs earlier in the same list.
- Isolation re-runs reuse your pytest options but drop arguments that name test paths. Options like `-k` or `-m` that exclude the target will make isolation report "unknown" for that test.
- `-p no:randomly` is passed to `why` probes so ordering stays fixed; if you rely on a random-order plugin, reproduce with its seed.
- Cause hints are keyword heuristics and will miss or mislabel causes.

## Related tools

flakehunt is not the first tool near this problem:

- [`pytest-flakefinder`](https://github.com/dropbox/pytest-flakefinder) repeats tests to expose flakiness (pytest plugin).
- [`asottile/detect-test-pollution`](https://github.com/asottile/detect-test-pollution) finds polluting tests for pytest and is a good option if that is all you need.
- [`box/flaky`](https://github.com/box/flaky) and similar retry plugins *hide* flakes by rerunning; flakehunt is for finding them.
- RSpec has `--bisect` built in for the same job in Ruby.

What flakehunt adds is one workflow: runner-agnostic detection from JUnit, automatic triage into intrinsic / broken / order-dependent, and the bisect, in one dependency-free CLI.

## Roadmap

- `why` adapters for jest/vitest and `go test` (the seam is `PytestSession` in `src/flakehunt/why.py`)
- run history file to catch low-rate flakes across CI runs
- `--deselect` / quarantine list output
- verified recipes for more runners (open an issue using the "Runner recipe" template)

## Contributing

Small, dependency-free, offline: see [CONTRIBUTING.md](CONTRIBUTING.md). The most useful contribution is a runner recipe you have actually run.

## License

[MIT](LICENSE). Research notes behind the project: [docs/research.md](docs/research.md).
