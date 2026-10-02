# Research notes

Snapshot taken 2026-10-02 from GitHub's weekly/monthly trending pages, a few README reads, and
web searches. Star counts are as displayed that day and will have moved. Rows marked
*(listing only)* are based on the trending-page description, not a read of the README.

## What is spreading right now

Almost everything fast-growing is **agent infrastructure**: harnesses, skills, memory, context
control, parallel-agent managers. Outside that: local/offline media tools and small,
single-purpose CLIs with a GIF in the README.

| Project | What it is | Approx. attention | Why it spreads / gap |
|---|---|---|---|
| paperclipai/paperclip | App to manage agents at work | 96k stars, +14k in a week *(listing only)* | Timely framing, broad audience |
| vectorize-io/hindsight | Agent memory that learns | 44.6k, +17k/wk *(listing only)* | Memory is the top agent pain point |
| debpalash/VoiceStudio | Fully local ElevenLabs alternative | 51.7k, +16k/wk *(listing only)* | "Local, free replacement" is a proven hook |
| affaan-m/ECC | Agent harness optimisation | 271k, +26k/mo *(listing only)* | Bundles many tips; hard to tell what is verified |
| pbakaus/impeccable | Design language for AI harnesses | 74k *(listing only)* | Taste as a skill; visual output sells itself |
| heygen-com/hyperframes | HTML to video, built for agents | 55.7k *(listing only)* | Clear before/after |
| alibaba/open-code-review | Deterministic pipeline + LLM review | 43k, +21k/mo *(listing only)* | Pairs rules with LLM; needs model access |
| mksglu/context-mode | MCP server that sandboxes tool output | ~25k | README read: strong "315 KB to 5.4 KB" claim, 17-platform install matrix. Gap: install friction varies by platform, claims are self-reported |
| NVIDIA/SkillSpector | Security scanner for agent skills | ~19k | README read: static + optional LLM pass, SARIF output. Gap: static only, English-centric |
| max-sixty/worktrunk | CLI for git worktrees and parallel agents | ~8.7k | README read: GIF demos, brew/cargo/winget. Small tool, one clear job |
| trycua/cua | Computer-use drivers and benchmarks | 27.8k *(listing only)* | Infra for a hot area |
| tashfeenahmed/freellmapi | 34 free LLM providers behind one API | 30k *(listing only)* | "Free" hook |
| pablostanley/yoinks | Download any video from the terminal | 3.3k, +1k/wk *(listing only)* | Tiny, memorable, single command |
| microsoft/markitdown | Files to Markdown | ~184k, +4.7k/wk (search result) | Boring, universally useful utility |
| stablyai/orca | IDE for fleets of parallel agents | ~68k, +5k/wk (search result) | Parallel agents are the workflow shift |
| tt-a1i/archify | Agent skill producing architecture diagrams as HTML | 76k *(listing only)* | Visual artefact in one step |

### Patterns

1. **One job, one command, visible result.** worktrunk, yoinks, markitdown.
2. **Agent-adjacent beats agent-core.** Tooling *around* agents (context, skills, worktrees) grows faster than yet another agent.
3. **A GIF or screenshot at the top.** Every high-growth README read led with a demo.
4. **Strong numbers in the hook** ("98% reduction") drive shares, but are mostly self-reported. Reproducible claims are an open lane.
5. **Local, offline, no keys** is a recurring selling point.

### The crowding problem

Searching each agent-adjacent idea showed it was already occupied: AGENTS.md/CLAUDE.md linters
(`agents-lint`, `agents-md-check`, `ctxlint`), repo-config scanners for malicious `.claude/`
and `.mcp.json` (`dotclaude-security`, `sketchy`, `mcpscan`), lockfile diff tools (`lockdelta`,
`lockreview`, `lockscope`, `lockfile-diff`). Adding a tenth entry to a saturated list is not
useful, so those were rejected.

## Ideas considered

| # | Idea | Verdict |
|---|---|---|
| 1 | AGENTS.md / CLAUDE.md staleness linter | Rejected: several existing tools |
| 2 | Pre-open scanner for untrusted repos' agent config | Rejected: several existing tools |
| 3 | Human-readable lockfile diff with supply-chain flags | Rejected: several existing tools |
| 4 | Agent session-log miner for repeated failures | Rejected: overlaps existing agent-log tooling, depends on private log formats |
| 5 | **Flaky-test hunter with polluter bisect** | **Chosen** |
| 6 | Env-var drift detector (code vs `.env.example` vs CI) | Useful, but low shareability and demo is a table |
| 7 | Merge-conflict forecaster for parallel worktrees | Rejected: exists |
| 8 | LLM CI-log summariser | Rejected: "AI wrapper", needs paid API |
| 9 | Local webhook inspector | Rejected: crowded, close to CRUD |
| 10 | Test-impact selection without coverage data | Rejected: hard to make reliable across languages |

## Why flakehunt

- **Real, universal pain** that gets worse with fast AI-generated test suites and parallel agents editing the same repo.
- **Different mechanism** from "lint the config" tools: it *runs* things and reasons about outcomes. Delta debugging is a credible, well-understood technique rather than a prompt.
- **Immediate demo, no keys**: `flakehunt demo` shows the entire value in about ten seconds.
- **Honest neighbours**: [`detect-test-pollution`](https://github.com/asottile/detect-test-pollution) (205 stars) does pytest polluter search; [`pytest-flakefinder`](https://github.com/dropbox/pytest-flakefinder) (158) repeats tests; retry plugins hide flakes; RSpec has `--bisect`. The gap is a runner-agnostic detector that also triages *why* and feeds the bisect.
- **Low maintenance**: standard library, JUnit XML as the contract, one adapter seam for new runners.
- **Contribution surface**: runner recipes, cause hints, `why` adapters.

Name check: no `flakehunt` package on PyPI or npm and no repository with that name on GitHub at the time of writing.
