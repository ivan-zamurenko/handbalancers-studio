# Evidence contract

A task result states task ID, changed paths, behavior delivered, RED command and failure, GREEN command and result, affected regressions, review findings, outstanding external gates, Git commit/push status and next task ID. No secrets or user videos.

The repository owns the canonical template `.workflow/evidence/TEMPLATE.json`. A result is not `done` just because a document was written. For an external gate report the actual test environment and provider behavior; unavailable is pending/blocked. Approval to test is not successful testing.

Do not place the final commit's own SHA inside a file in that same commit. Store base SHA and branch in evidence; return resulting SHA in the final message or a subsequent checkpoint. Independent reviewers do not edit the writer's state or migrations.

When pausing mid-RED, preserve failing test, dirty paths, last exact command and minimal next action. Do not make a green-looking empty assertion, `skip`, or `xfail` to close the task. A discovered defect in a test is explained against the original acceptance criterion before changing it.
