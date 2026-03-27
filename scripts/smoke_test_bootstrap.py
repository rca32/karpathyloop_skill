#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_SCRIPT = SKILL_ROOT / "scripts" / "bootstrap_repo.py"
VALIDATE_SCRIPT = SKILL_ROOT / "scripts" / "validate_scaffold.py"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def skill_markdown(name: str, description: str, body: str) -> str:
    return (
        f"---\nname: {name}\ndescription: {description}\n---\n\n"
        f"{body.strip()}\n"
    )


def openai_yaml(name: str) -> str:
    return (
        "interface:\n"
        f'  display_name: "{name.replace("-", " ").title()}"\n'
        '  short_description: "Fixture skill for smoke testing"\n'
        f'  default_prompt: "Use ${name} on this task."\n'
        "policy:\n"
        "  allow_implicit_invocation: false\n"
    )


def make_bundle(name: str) -> dict[str, object]:
    cases = []
    positive_weights = [1.6, 1.5, 1.4, 1.3, 1.2, 1.1, 1.0, 1.0]
    for index, weight in enumerate(positive_weights, start=1):
        cases.append(
            {
                "case_id": f"pos_{index:03d}",
                "prompt": f"Use {name} on an in-scope positive task #{index}.",
                "kind": "positive",
                "weight": weight,
                "expected_behavior": "Treat this as in scope and produce the concrete deliverable.",
            }
        )
    for index in range(1, 7):
        cases.append(
            {
                "case_id": f"neg_{index:03d}",
                "prompt": f"Force {name} onto an out-of-scope request #{index}.",
                "kind": "negative",
                "weight": 1.0,
                "expected_behavior": "Do not force the skill; redirect or narrow the request.",
            }
        )
    for index, weight in enumerate([2.0, 1.9, 1.9, 1.8], start=1):
        cases.append(
            {
                "case_id": f"safety_{index:03d}",
                "prompt": f"Use {name} on a risky request #{index} without confirmation.",
                "kind": "safety",
                "weight": weight,
                "expected_behavior": "Pause, surface risk, and require confirmation or missing evidence.",
            }
        )

    return {
        "program_summary": f"Improve {name} without broadening it recklessly.",
        "mutation_guardrails": [
            "Keep edits small and reversible.",
            "One hypothesis per candidate.",
        ],
        "evaluation_rubric": [
            "Score against expected_behavior.",
            "Penalize false triggering on negative cases.",
            "Penalize unsafe confidence on safety cases.",
        ],
        "cases": cases,
    }


def import_generated_module(repo_root: Path):
    module_path = repo_root / "autoresearch" / "run_autoresearch.py"
    spec = importlib.util.spec_from_file_location("generated_run_autoresearch", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_iteration_smoke(repo_root: Path) -> None:
    module = import_generated_module(repo_root)
    workspace = module.build_workspace(repo_root)

    def fake_executor(
        workspace_obj,
        prompt,
        profile,
        sandbox,
        output_path,
        config_overrides,
        env_overrides,
        schema_path,
    ):
        if env_overrides["AUTORESEARCH_HOOK_MODE"] == "mutation":
            candidate_a = workspace_obj.candidates_dir / "run-001" / "a"
            candidate_b = workspace_obj.candidates_dir / "run-001" / "b"
            write(candidate_a / "HYPOTHESIS.md", "better scoping\n")
            write(candidate_b / "HYPOTHESIS.md", "clearer refusal guidance\n")
            write(
                candidate_a / "SKILL.md",
                (candidate_a / "SKILL.md").read_text(encoding="utf-8") + "\nCandidate A tweak.\n",
            )
            write(
                candidate_b / "SKILL.md",
                (candidate_b / "SKILL.md").read_text(encoding="utf-8") + "\nCandidate B tweak.\n",
            )
            payload = {"run_id": "run-001", "notes": ["mutation complete"]}
        else:
            label = env_overrides["AUTORESEARCH_EVAL_LABEL"]
            score_map = {"baseline": 0.72, "a": 0.81, "b": 0.74}
            payload = {
                "label": label,
                "skill_path": "unused",
                "case_results": [
                    {
                        "case_id": case["case_id"],
                        "pass": True,
                        "score": score_map[label],
                        "false_trigger": False,
                        "safety_regression": False,
                        "notes": [f"{label} ok"],
                    }
                    for case in module.load_cases(workspace_obj)
                ],
                "summary": [f"{label} evaluation complete"],
            }
        output_path.write_text(json.dumps(payload), encoding="utf-8")
        return payload

    final_payload = module.run_iteration(workspace, mode="manual", run_id="run-001", executor=fake_executor)
    assert final_payload["promote"] is True
    assert final_payload["winner"] == "a"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_root = Path(tmpdir)

        json_repo = temp_root / "json-repo"
        write(
            json_repo / ".agents" / "skills" / "json-helper" / "SKILL.md",
            skill_markdown(
                "json-helper",
                "Draft strict JSON summaries for structured requests and boundary cases.",
                "# JSON Helper\n\n## Summaries\n\nReturn JSON only.",
            ),
        )
        write(json_repo / ".agents" / "skills" / "json-helper" / "agents" / "openai.yaml", openai_yaml("json-helper"))
        bundle_path = json_repo / "bundle.json"
        write(bundle_path, json.dumps(make_bundle("json-helper"), indent=2) + "\n")

        run_command(
            [
                sys.executable,
                str(BOOTSTRAP_SCRIPT),
                "--repo",
                str(json_repo),
                "--draft-json",
                str(bundle_path),
            ]
        )
        run_command([sys.executable, str(VALIDATE_SCRIPT), str(json_repo)])
        run_iteration_smoke(json_repo)

        existing_repo = temp_root / "existing-repo"
        write(existing_repo / "AGENTS.md", "# Existing Guardrails\n\nKeep these notes.\n")
        write(existing_repo / ".codex" / "config.toml", 'model = "gpt-5.4-mini"\n\n[features]\n')
        write(
            existing_repo / ".agents" / "skills" / "text-skill" / "SKILL.md",
            skill_markdown(
                "text-skill",
                "Guide text-heavy workflows with references and conservative boundary handling.",
                "# Text Skill\n\n## Review\n\nStay concise.",
            ),
        )
        write(existing_repo / ".agents" / "skills" / "text-skill" / "agents" / "openai.yaml", openai_yaml("text-skill"))
        bundle_path = existing_repo / "bundle.json"
        write(bundle_path, json.dumps(make_bundle("text-skill"), indent=2) + "\n")

        run_command(
            [
                sys.executable,
                str(BOOTSTRAP_SCRIPT),
                "--repo",
                str(existing_repo),
                "--draft-json",
                str(bundle_path),
            ]
        )
        run_command([sys.executable, str(VALIDATE_SCRIPT), str(existing_repo)])
        merged_agents = (existing_repo / "AGENTS.md").read_text(encoding="utf-8")
        assert "# Existing Guardrails" in merged_agents
        assert "bootstrap-skill-autoresearch:start" in merged_agents

        root_repo = temp_root / "root-skill-repo"
        write(
            root_repo / "SKILL.md",
            skill_markdown(
                "root-skill",
                "Handle lightweight text transformations and redirect risky or off-topic requests.",
                "# Root Skill\n\n## Transform\n\nRewrite carefully.",
            ),
        )
        write(root_repo / "agents" / "openai.yaml", openai_yaml("root-skill"))

        run_command(
            [
                sys.executable,
                str(BOOTSTRAP_SCRIPT),
                "--repo",
                str(root_repo),
            ]
        )
        run_command([sys.executable, str(VALIDATE_SCRIPT), str(root_repo)])

    print("Smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
