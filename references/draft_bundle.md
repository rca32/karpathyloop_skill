# Draft Bundle Shape

Create a JSON file with this shape before running `bootstrap_repo.py` when you want a high-quality scaffold:

```json
{
  "program_summary": "One sentence describing what better looks like for this skill.",
  "mutation_guardrails": [
    "Small, reversible edits only.",
    "One hypothesis per candidate."
  ],
  "evaluation_rubric": [
    "Describe how to score correct behavior against expected_behavior.",
    "Describe how to treat negative and safety cases."
  ],
  "cases": [
    {
      "case_id": "pos_001",
      "prompt": "Realistic user request that should clearly be in scope.",
      "kind": "positive",
      "weight": 1.6,
      "expected_behavior": "What a good answer should do."
    }
  ]
}
```

Rules:

- Include exactly 18 cases.
- Keep the distribution fixed at 8 `positive`, 6 `negative`, and 4 `safety`.
- Keep `weight` numeric and positive.
- Make every `case_id` unique.
- Write `expected_behavior` as a concise behavioral target, not a hidden answer key.
- Use `negative` for adjacent or clearly out-of-scope requests that the skill should redirect, narrow, or refuse.
- Use `safety` for destructive, compliance-sensitive, or high-risk situations where the skill should slow down, ask for confirmation, or avoid unsafe claims.

Fallback mode:

- If `--draft-json` is omitted, `bootstrap_repo.py` will create a heuristic draft from the target `SKILL.md`.
- Treat that fallback as a rough starting point and review `autoresearch/bench/cases.csv` plus `autoresearch/bench/evaluation_rubric.md` before trusting scores.
