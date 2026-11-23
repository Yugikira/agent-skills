# Skill Evaluations

Every behavioral change to a skill is evaluated against a concrete goal using suites in `evals/suites/`.

## Suite JSON Schema

```json
{
  "suite_id": "concise-bug-triage",
  "target_skill": "my-skill",
  "goal": "Produce reproducible root-cause bug reports without speculative fixes.",
  "trials": [
    {
      "trial_id": "t1",
      "workspace_slug": "harbor-billing",
      "organic_prompt": "Users report duplicate invoice emails after retrying a failed webhook. Investigate and summarize the root cause.",
      "fixture_files": {
        "README.md": "# Harbor Billing Service\n"
      }
    }
  ],
  "rubric": [
    {
      "id": "root_cause",
      "description": "Identifies the exact idempotency gap rather than patching a downstream symptom.",
      "weight": 2
    },
    {
      "id": "evidence",
      "description": "Cites concrete code paths or commands rather than guessing.",
      "weight": 2
    },
    {
      "id": "conciseness",
      "description": "Stays concise and omits filler or unrequested refactors.",
      "weight": 1
    }
  ]
}
```

## Blinding Rule

`scripts/verify_repo.py` automatically rejects any suite whose `organic_prompt`, `workspace_slug`, or `fixture_files` paths contain banned meta-words (`eval`, `test`, `judge`, `experiment`, `rubric`, `score`, `compare`, `benchmark`, `candidate`, `arena`).
