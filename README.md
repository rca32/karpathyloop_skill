# karpathyloop_skill

`karpathyloop_skill` is a Codex-skill take on the Karpathy-style autoresearch loop.

If [karpathy/autoresearch](https://github.com/karpathy/autoresearch) asks, "what happens when agents iterate on a tiny real training setup all night?", this repo asks a sibling question: "what happens when the thing being improved is a Codex skill?"

The answer is not "full autonomy, no brakes." The answer is a tighter loop: one target skill, a benchmark you can actually read, guardrails you can review, and promotion rules that make small wins count only when they are real.

## Read This In

- [English](README.md)
- [한국어](README.ko.md)
- [日本語](README.ja.md)
- [简体中文](README.zh-CN.md)

## What Is the Karpathy Loop?

In March 2026, Andrej Karpathy published [`autoresearch`](https://github.com/karpathy/autoresearch), a deliberately compact experiment in agent-driven research. The core idea is simple and sharp:

- Keep the mutable surface small.
- Make evaluation cheap and repeatable.
- Compare against a baseline instead of vibes.
- Let agents iterate, but only inside clear boundaries.

That idea is the inspiration here. This repository is not an official Karpathy project, and it does not bundle his training stack. Instead, it translates the same operating style into the world of Codex skills.

So instead of agents editing `train.py`, they improve a single `SKILL.md`. Instead of model metrics, they face benchmark cases, false-trigger counts, and safety checks. Same rhythm, different battlefield.

## What This Repository Does

Point the bootstrap script at a repository that contains exactly one Codex skill, and it scaffolds the pieces needed for a controlled improvement loop:

- `AGENTS.md` guardrails
- benchmark cases and an evaluation rubric
- evaluator, mutator, and failure-miner agent definitions
- Codex hooks and config wiring
- a reusable `autoresearch/run_autoresearch.py` runner
- run artifacts, candidate workspaces, and a leaderboard

The goal is to remove the annoying setup work around skill iteration. You should spend your time improving the benchmark and the skill, not rebuilding the harness every time.

## Why This Shape Works for Skills

Skill iteration often goes sideways in boring, predictable ways:

- prompts get longer but not better
- evaluation is inconsistent, so nobody trusts the score
- edits wander outside the intended scope
- safety behavior gets hand-waved until it breaks at the worst moment

`karpathyloop_skill` is designed to keep that from happening.

- Small mutable scope: the target is one skill, not the whole repo.
- Human-owned policy: the benchmark, rubric, hooks, and promotion logic stay reviewable.
- Cheap comparisons: baseline vs. candidate `a` vs. candidate `b`.
- Conservative promotion: regressions are not allowed to sneak in behind a prettier average score.

## How the Loop Works Here

The generated workflow is intentionally narrow:

1. Detect the target skill.
   The bootstrap step looks for exactly one skill in the repo root, `.agents/skills/*`, or `skills/*`. If there is more than one, you must pass `--skill-path`.
2. Build the benchmark bundle.
   You can provide a draft JSON bundle, or let the script synthesize a rough first pass from `SKILL.md`.
3. Scaffold the repo.
   The scripts write the benchmark assets, hooks, agent definitions, config, and reusable runner.
4. Validate immediately.
   The validator checks file presence, benchmark shape, hook wiring, config profiles, and the generated runner contract.
5. Run an iteration.
   The generated runner evaluates the baseline plus two candidates and records everything under `autoresearch/runs/<RUN_ID>/`.
6. Promote only if the result earns it.
   A candidate must improve the weighted mean score, avoid negative-case regressions, avoid safety regressions, and justify oversized `SKILL.md` growth.

### Current Run Model

- Two candidates are created under `autoresearch/candidates/<RUN_ID>/a` and `.../b`.
- Mutation is limited to the approved candidate paths or the target skill path.
- Evaluation is read-only and must return structured JSON.
- Each candidate must leave a `HYPOTHESIS.md` describing its one hypothesis.

### Current Promotion Rules

As implemented today, a candidate is promoted only if all of these are true:

- weighted mean score improves by at least `0.03`
- negative-case false triggers do not increase
- safety regressions stay at `0`
- if `SKILL.md` grows by more than `15%`, the score gain must be at least `0.05`

That gate is intentionally strict. The point is not to reward activity. The point is to reward trustworthy improvement.

## What Gets Generated

Running the bootstrap against a target repo writes or merges the core autoresearch surface:

- `AGENTS.md`
  Repository-level guardrails that define what stays human-owned and what is mutable during runs.
- `autoresearch/program.md`
  The program summary and mutation guidance for the target skill.
- `autoresearch/bench/cases.csv`
  The fixed benchmark case list with exactly 18 rows: 8 `positive`, 6 `negative`, and 4 `safety`.
- `autoresearch/bench/evaluation_rubric.md`
  Evaluator guidance for scoring behavior.
- `autoresearch/bench/final_schema.json`
  The expected final JSON shape for runs.
- `autoresearch/root_prompt.txt`
  The execution prompt used by the runner.
- `autoresearch/run_autoresearch.py`
  The reusable baseline-plus-two-candidates loop.
- `autoresearch/runs/<RUN_ID>/`
  Per-run baseline evaluation, candidate evaluations, mutation outputs, and final results.
- `autoresearch/candidates/<RUN_ID>/`
  Candidate copies edited during mutation.
- `autoresearch/leaderboard.json`
  Run history and best promoted score.
- `.codex/config.toml`
  Managed Codex profiles and agent settings.
- `.codex/hooks.json` and `.codex/hooks/`
  Hook wiring plus helper scripts for context loading and eval JSON enforcement.
- `.codex/agents/`
  Evaluator, mutator, and failure-miner agent definitions.

Existing `AGENTS.md`, `.codex/config.toml`, and `.codex/hooks.json` content is merged where possible instead of being wholesale replaced.

## Prerequisites

Before using this repository, make sure the following are true:

- your target repository contains exactly one Codex skill
- that skill lives at the repo root, `.agents/skills/<name>/`, or `skills/<name>/`
- Python 3 is available
- the Codex CLI is installed and reachable as `codex`
- you are prepared to review and own the generated benchmark, guardrails, and promotion behavior

If your Codex executable is not named `codex`, the generated runner also supports overriding it with the `CODEX_BIN` environment variable.

## Quick Start

Run these scripts from this repository against a separate target skill repository.

### 1. Preview the scaffold

Dry-run first so you can inspect the planned writes:

```bash
python3 scripts/bootstrap_repo.py \
  --repo /path/to/target-repo \
  --skill-path /path/to/target-repo/.agents/skills/my-skill \
  --draft-json /path/to/draft-bundle.json \
  --dry-run
```

If the target repo contains exactly one detectable skill, `--skill-path` is optional.

### 2. Materialize the scaffold

Once the preview looks right, run the same command without `--dry-run`:

```bash
python3 scripts/bootstrap_repo.py \
  --repo /path/to/target-repo \
  --skill-path /path/to/target-repo/.agents/skills/my-skill \
  --draft-json /path/to/draft-bundle.json
```

No draft bundle yet? You can still bootstrap with the fallback generator:

```bash
python3 scripts/bootstrap_repo.py \
  --repo /path/to/target-repo \
  --skill-path /path/to/target-repo/.agents/skills/my-skill
```

Fallback mode is useful for getting moving fast, but it is still a draft. Review the generated benchmark and rubric before you trust the numbers.

### 3. Validate immediately

```bash
python3 scripts/validate_scaffold.py /path/to/target-repo
```

For machine-readable output:

```bash
python3 scripts/validate_scaffold.py /path/to/target-repo --json
```

### 4. Run the first iteration

After bootstrap and validation, switch into the target repository and run:

```bash
python3 autoresearch/run_autoresearch.py --mode manual
```

The generated runner also accepts `--mode scheduled` for externally orchestrated use, but this repository does not set up a scheduler for you.

## Draft Bundle

If you want a better starting point, prepare a draft bundle JSON file before bootstrapping. The exact shape is documented in [references/draft_bundle.md](references/draft_bundle.md).

The bundle includes:

- `program_summary`
  One sentence describing what better behavior looks like.
- `mutation_guardrails`
  Constraints that keep edits small, reversible, and on-topic.
- `evaluation_rubric`
  Scoring guidance for the evaluator.
- `cases`
  Benchmark rows for positive, negative, and safety behavior.

Rules that matter:

- exactly 18 cases
- fixed distribution of 8 `positive`, 6 `negative`, and 4 `safety`
- unique `case_id` values
- positive numeric `weight`
- behavioral expectations, not hidden answer keys

Use an explicit draft bundle when the skill has sharp boundaries, expensive failure modes, or benchmark language that humans should review up front.

## Guardrails and Limitations

This project is constrained on purpose:

- it supports one target skill per repo in v1
- benchmark cases, hooks, config, and promotion rules are human-owned after bootstrap
- mutation is limited to the target skill or generated candidate directories
- evaluation runs are read-only and must return structured JSON
- bootstrap does not automatically start iterative research
- if the skill lives at the repository root, promotion preserves `.git`, `.codex`, `autoresearch`, and `AGENTS.md`

This is not trying to be an infinite autonomous optimizer. It is trying to be a disciplined loop you can trust on a Tuesday afternoon.

## Repository Layout

```text
.
|-- SKILL.md
|-- README.md
|-- agents/
|   `-- openai.yaml
|-- assets/
|   `-- templates/
|       |-- AGENTS.md.tmpl
|       |-- .codex/...
|       `-- autoresearch/...
|-- references/
|   `-- draft_bundle.md
`-- scripts/
    |-- bootstrap_repo.py
    |-- validate_scaffold.py
    `-- smoke_test_bootstrap.py
```

## Development and Verification

If you change this repository itself, run the smoke test before publishing:

```bash
python3 scripts/smoke_test_bootstrap.py
```

For deeper checks on a specific bootstrapped repository:

```bash
python3 scripts/validate_scaffold.py /path/to/target-repo --json
```

## A Small Naming Note

This README uses the public-facing name `karpathyloop_skill`. You may still see internal identifiers such as `bootstrap-skill-autoresearch` in metadata, markers, or generated sections while the repo naming catches up. The workflow and commands documented here match the current implementation.
