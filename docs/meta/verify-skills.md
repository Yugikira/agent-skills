## What it does

`verify-skills` is the repository's verification gate. It runs `scripts/verify_repo.py` to check YAML frontmatter, dual-harness invocation parity, relative links, line budgets, prose hygiene, README/docs/router sync, and eval blinding integrity, plus live smoke tests for repo scripts.

## When to reach for it

You invoke this by typing `/verify-skills`, and the agent will not reach for it on its own. Run it before committing any change to skills, docs, or eval suites, or when auditing the repository for drift.

## Common questions

**What does an outcome of `clean`, `changed`, or `blocked` mean?**
`clean` means every check passed with no edits needed. `changed` means verification drift was fixed and re-verified green. `blocked` means a genuine failure could not be resolved safely and needs your input.

**Can it edit my skill behavior to make a check pass?**
No. Never weaken a verification rule to turn a red check green; fix the underlying defect or report it.

## It's working if

- Broken links, missing `agents/openai.yaml` files, stale `README.md` entries, and accidental blinding leaks fail fast before merge.
- Every verification report cites exact commands and exit codes rather than claiming "looks good."
