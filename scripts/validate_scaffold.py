#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


EXPECTED_CASE_COLUMNS = [
    "case_id",
    "prompt",
    "kind",
    "weight",
    "expected_behavior",
]
EXPECTED_CASE_COUNTS = {"positive": 8, "negative": 6, "safety": 4}
REQUIRED_FILES = [
    "AGENTS.md",
    "autoresearch/program.md",
    "autoresearch/root_prompt.txt",
    "autoresearch/run_autoresearch.py",
    "autoresearch/bench/cases.csv",
    "autoresearch/bench/evaluation_rubric.md",
    "autoresearch/bench/final_schema.json",
    "autoresearch/leaderboard.json",
    ".codex/config.toml",
    ".codex/hooks.json",
    ".codex/agents/autoresearch_failure_miner.toml",
    ".codex/agents/autoresearch_skill_evaluator.toml",
    ".codex/agents/autoresearch_skill_mutator.toml",
    ".codex/hooks/autoresearch_session_context.py",
    ".codex/hooks/autoresearch_require_eval_json.py",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a bootstrapped autoresearch scaffold.")
    parser.add_argument("repo", help="Repository root to validate")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary")
    return parser.parse_args()


def load_cases(csv_path: Path) -> dict[str, Any]:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        raise ValueError("Benchmark CSV is empty.")
    if list(rows[0].keys()) != EXPECTED_CASE_COLUMNS:
        raise ValueError("Benchmark CSV columns do not match the expected contract.")

    counts = Counter()
    for row in rows:
        counts[row["kind"]] += 1
        if not row["case_id"] or not row["prompt"] or not row["expected_behavior"]:
            raise ValueError(f"Benchmark row is missing required text: {row}")
        weight = float(row["weight"])
        if weight <= 0:
            raise ValueError(f"Benchmark weight must be positive: {row['case_id']}")

    if len(rows) != 18 or dict(counts) != EXPECTED_CASE_COUNTS:
        raise ValueError(
            f"Unexpected benchmark shape: total={len(rows)} counts={dict(counts)}"
        )
    return {"rows": len(rows), "counts": dict(counts)}


def validate_config(config_path: Path) -> None:
    content = config_path.read_text(encoding="utf-8")
    features_enabled = False
    profile_names: set[str] = set()
    current_section = None  # type: str | None

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            header = line[1:-1].strip()
            if header == "features":
                current_section = "features"
            elif header.startswith("profiles."):
                current_section = "profiles"
                profile_names.add(header.split(".", 1)[1])
            else:
                current_section = None
            continue

        if current_section == "features" and "=" in line:
            key, value = [part.strip() for part in line.split("=", 1)]
            if key == "codex_hooks":
                features_enabled = value.lower() == "true"

    if not features_enabled:
        raise ValueError(".codex/config.toml must enable features.codex_hooks = true")

    if "autoresearch_mutate" not in profile_names or "autoresearch_eval" not in profile_names:
        raise ValueError("Both autoresearch profiles must exist in .codex/config.toml")


def validate_hooks(hooks_path: Path) -> None:
    payload = json.loads(hooks_path.read_text(encoding="utf-8"))
    hooks = payload.get("hooks", {})
    session = hooks.get("SessionStart", [])
    stop = hooks.get("Stop", [])
    session_command = (
        'python3 "$(git rev-parse --show-toplevel)/.codex/hooks/autoresearch_session_context.py"'
    )
    stop_command = (
        'python3 "$(git rev-parse --show-toplevel)/.codex/hooks/autoresearch_require_eval_json.py"'
    )

    if not any(
        entry.get("matcher") == "startup|resume"
        and any(hook.get("command") == session_command for hook in entry.get("hooks", []))
        for entry in session
    ):
        raise ValueError("SessionStart hook for autoresearch_session_context.py is missing.")

    if not any(
        any(hook.get("command") == stop_command for hook in entry.get("hooks", []))
        for entry in stop
    ):
        raise ValueError("Stop hook for autoresearch_require_eval_json.py is missing.")


def validate_program_doc(program_path: Path) -> None:
    content = program_path.read_text(encoding="utf-8")
    if "python3 autoresearch/run_autoresearch.py --mode scheduled" not in content:
        raise ValueError("Program doc must document the scheduled automation entrypoint.")
    if "same promotion gate as manual runs" not in content:
        raise ValueError("Program doc must warn that scheduled runs use the same promotion gate.")
    if "update the live skill" not in content:
        raise ValueError("Program doc must warn that scheduled runs may update the live skill.")


def import_run_module(repo_root: Path):
    module_path = repo_root / "autoresearch" / "run_autoresearch.py"
    spec = importlib.util.spec_from_file_location("bootstrapped_run_autoresearch", module_path)
    if spec is None or spec.loader is None:
        raise ValueError("Could not import generated autoresearch/run_autoresearch.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_run_module(repo_root: Path) -> dict[str, Any]:
    module = import_run_module(repo_root)
    workspace = module.build_workspace(repo_root)
    cases = module.load_cases(workspace)
    if len(cases) != 18:
        raise ValueError("Generated run_autoresearch.py did not load 18 benchmark cases.")

    help_completed = subprocess.run(
        [sys.executable, str(repo_root / "autoresearch" / "run_autoresearch.py"), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    normalized_help = re.sub(r"\s+", " ", help_completed.stdout)
    if "Codex automation entrypoint" not in normalized_help:
        raise ValueError("Generated run_autoresearch.py help must describe the automation entrypoint.")
    if "same promotion gate" not in normalized_help:
        raise ValueError("Generated run_autoresearch.py help must describe the shared promotion gate.")
    if "live skill" not in normalized_help:
        raise ValueError("Generated run_autoresearch.py help must warn that scheduled runs can update the live skill.")
    if "woken from sleep" not in normalized_help:
        raise ValueError("Generated run_autoresearch.py help must mention the wake guard for scheduled runs.")

    with tempfile.TemporaryDirectory(dir=workspace.candidates_dir) as tempdir:
        output_path = Path(tempdir) / "last_message.json"
        captured_cmd = None  # type: list[str] | None

        def fake_run(cmd, cwd, input, text, env, check):  # noqa: ANN001
            nonlocal captured_cmd
            captured_cmd = list(cmd)
            output_path.write_text("{}", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0)

        original_run = module.subprocess.run
        module.subprocess.run = fake_run
        try:
            payload = module.invoke_codex_exec(
                workspace,
                prompt="validation prompt",
                profile="autoresearch_eval",
                sandbox="read-only",
                output_path=output_path,
                config_overrides=None,
                env_overrides={},
                schema_path=None,
            )
        finally:
            module.subprocess.run = original_run

    if captured_cmd is None:
        raise ValueError("Generated run_autoresearch.py did not invoke codex exec.")
    if "-a" in captured_cmd:
        raise ValueError("Generated run_autoresearch.py must not pass the deprecated -a flag.")
    if payload != {}:
        raise ValueError("Generated run_autoresearch.py must parse the last message JSON correctly.")

    with tempfile.TemporaryDirectory(dir=workspace.candidates_dir) as tempdir:
        marker = Path(tempdir)
        if not marker.exists():
            raise ValueError("Could not create a temporary directory under autoresearch/candidates")

    return {
        "skill_dir": str(workspace.skill_dir),
        "cases_loaded": len(cases),
        "runner_help": "ok",
    }


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo).resolve()
    results: dict[str, Any] = {"repo_root": str(repo_root), "checks": {}}

    try:
        missing = [path for path in REQUIRED_FILES if not (repo_root / path).exists()]
        if missing:
            raise ValueError(f"Missing required files: {', '.join(missing)}")

        results["checks"]["files"] = {"required_files": len(REQUIRED_FILES)}
        results["checks"]["benchmark"] = load_cases(repo_root / "autoresearch" / "bench" / "cases.csv")
        validate_program_doc(repo_root / "autoresearch" / "program.md")
        results["checks"]["automation_docs"] = {"status": "ok"}
        validate_config(repo_root / ".codex" / "config.toml")
        results["checks"]["config"] = {"profiles": ["autoresearch_mutate", "autoresearch_eval"]}
        validate_hooks(repo_root / ".codex" / "hooks.json")
        results["checks"]["hooks"] = {"status": "ok"}
        results["checks"]["run_module"] = validate_run_module(repo_root)

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("Scaffold is valid.")
        return 0
    except Exception as exc:  # noqa: BLE001
        if args.json:
            print(json.dumps({"repo_root": str(repo_root), "error": str(exc)}, indent=2))
        else:
            print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
