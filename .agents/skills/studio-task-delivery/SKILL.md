---
name: studio-task-delivery
description: Execute or review one approved Handbalancer Studio task card using test-first development and a small auditable commit. Use for Studio roadmap task IDs, not unrelated coding or broad product planning.
---

# Studio task delivery

Input: one v4 task card, current checkout, `.workflow/CURRENT.md`. Output: bounded implementation or review, actual test evidence, task state/checkpoint, commit/push status. Requires a writable coding workspace and shell for implementation; no connected account is required. A chat without execution tools must not claim it ran tests or Git.

## Select and bound
Read root AGENTS.md once per session. Resolve the active task with `python tools/roadmap.py next` when the utility exists; otherwise read state and dependencies directly. Resume an in-progress task before starting another. Load only the task card and its relevant documents. Do not re-review the full reference archive before every edit.

Keep one observable responsibility per task. If the card cannot fit a coherent small commit after reading the code, create explicit child cards preserving its acceptance tests. Do not silently relax the requirement or use the split as an excuse for another architecture essay.

## Implement
Write the named behavior tests first. Run them; distinguish an actual absent-behavior RED from a broken environment. Record the command and failure. Implement the smallest complete behavior and get GREEN, then run the affected regressions. Keep tests and code in the same green commit; the evidence records chronology. Never alter expected behavior merely to make existing code pass.

For DB writes use the real isolated PostgreSQL/Supabase test boundary, include ownership, transaction rollback and concurrency where the card requires them. For UI behavior verify the relevant view in both themes and narrow/wide layouts; use provided C1/A1/C3 references, not a new visual direction. External SDK fakes verify a contract, not live provider readiness.

Before committing inspect the scoped diff and secret exposure. Do not stage unrelated changes, reset a user's work, force push, mutate old databases or deploy. Push only to a confirmed remote/task branch. Missing remote is a pending push, not a failed local implementation.

## Review
When asked to review, do not modify code. Compare the card against the actual diff, assertions, negative cases and executed evidence. Report concrete findings with location and reproduction or missing test. A clean local suite is not proof of a live OAuth/video/billing service. Use `references/evidence-and-handoff.md` for the expected result shape.

## Stop and hand over
Mark blocked external gates honestly, then select only independent eligible work. Preserve UNKNOWN for methodology/provider/privacy decisions not supplied by the owner. Update checkpoint with one exact next step. Never fabricate a SHA, test run, provider access or implementation completion. All source cards begin todo.
