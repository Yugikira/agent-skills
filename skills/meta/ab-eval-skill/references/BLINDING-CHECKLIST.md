# Blinding & Repeatability Checklist

Check every item before trusting an A/B verdict.

## Blinding Controls

- [ ] Zero banned meta-words (`eval`, `test`, `judge`, `experiment`, `rubric`, `score`, `compare`, `benchmark`, `candidate`, `arena`) in workspace directory names, filenames, or candidate prompts.
- [ ] Workspace directories use neutral, project-shaped names (for example, `harbor-service` and `cedar-service`).
- [ ] Candidate prompt asks for the real user outcome and never mentions Variant A, Variant B, or other runs.
- [ ] Rubric is withheld from candidates and provided only to the judge.
- [ ] Judge sees randomized blind labels (`alpha`, `beta`) per trial, never model names or `baseline`/`new`.

## Repeatability & Validity Controls

- [ ] At least 3 trials per variant (5+ when the margin is narrow), alternating order (`A, B, A, B`).
- [ ] Every trial actually executed the intended task (errors, timeouts, or skipped steps counted explicitly).
- [ ] Transcript check confirms the skill under test was actually loaded (or measures trigger rate honestly if testing a model-invoked pointer).
- [ ] Human or coordinator read outputs directly and compared against the judge verdict.
