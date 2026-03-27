---
name: bootstrap-skill-autoresearch
description: Turn a single-skill Codex repository into a self-improving autoresearch workspace. Use when a repo currently has exactly one target skill and Codex needs to add AGENTS.md guardrails, autoresearch benchmarks, evaluator/mutator agents, hooks, and a generic run loop without actually running the mutation loop yet.
---

# Bootstrap Skill Autoresearch

## Overview

Create a reusable autoresearch scaffold for one target skill. Favor deterministic bootstrap scripts for file generation and validation, while using Codex reasoning to draft the benchmark bundle.

## Workflow

1. Detect the target repository and skill path.
   - Prefer auto-detection only when exactly one skill exists.
   - Search the repo root, `.agents/skills/*`, and `skills/*`.
   - If more than one skill is present, stop and ask the user for the exact target path.
2. Read the target `SKILL.md` and draft a bootstrap bundle.
   - Include `program_summary`, `mutation_guardrails`, `evaluation_rubric`, and exactly 18 benchmark cases.
   - Keep benchmark columns fixed as `case_id,prompt,kind,weight,expected_behavior`.
   - Use 8 `positive`, 6 `negative`, and 4 `safety` cases.
   - Prefer realistic in-scope requests for positives, adjacent-but-out-of-scope requests for negatives, and risky/destructive variants for safety.
   - Use the exact JSON shape documented in [draft_bundle.md](./references/draft_bundle.md).
3. Preview the scaffold first.
   - Run:
   ```bash
   python3 /Users/infomax/.codex/skills/bootstrap-skill-autoresearch/scripts/bootstrap_repo.py \
     --repo /path/to/repo \
     --skill-path /path/to/skill \
     --draft-json /path/to/draft-bundle.json \
     --dry-run
   ```
   - Use the fallback bundle only when a rough first pass is acceptable:
   ```bash
   python3 /Users/infomax/.codex/skills/bootstrap-skill-autoresearch/scripts/bootstrap_repo.py \
     --repo /path/to/repo \
     --skill-path /path/to/skill
   ```
4. Materialize the scaffold.
   - Re-run without `--dry-run`.
   - Preserve existing `AGENTS.md`, `.codex/config.toml`, and `.codex/hooks.json` content. Only add the autoresearch-managed block or missing sections.
   - Do not run actual autoresearch iterations during bootstrap.
5. Validate immediately.
   - Run:
   ```bash
   python3 /Users/infomax/.codex/skills/bootstrap-skill-autoresearch/scripts/validate_scaffold.py /path/to/repo
   ```
   - Check that benchmark shape, hook wiring, agent files, and the generated `run_autoresearch.py` contract all pass.
6. Stop after bootstrap and validation.
   - Do not launch mutation/evaluation runs automatically.
   - Give the user the next command to run, typically:
   ```bash
   python3 autoresearch/run_autoresearch.py --mode manual
   ```

## Guardrails

- Support only one target skill per repo in v1.
- Treat benchmark cases, promotion logic, hooks, and Codex config as human-owned after bootstrap.
- Keep candidate mutation scope limited to the target skill or `autoresearch/candidates/<RUN_ID>/`.
- Prefer explicit benchmark drafts over generic fallback bundles when quality matters.
- If the repo-root itself is the skill, preserve `.git`, `.codex`, `autoresearch`, and `AGENTS.md` during candidate copy/promotion.

## Resources

- `scripts/bootstrap_repo.py`: Materialize the scaffold, merge managed config, and write benchmark assets.
- `scripts/validate_scaffold.py`: Validate the generated scaffold without running autoresearch.
- `scripts/smoke_test_bootstrap.py`: Create temporary fixture repos and exercise the bootstrap flow end to end.
- `references/draft_bundle.md`: Exact JSON shape for the drafted benchmark/rubric bundle.
- `assets/templates/`: File templates for `AGENTS.md`, `autoresearch/`, `.codex/agents/`, and `.codex/hooks/`.
