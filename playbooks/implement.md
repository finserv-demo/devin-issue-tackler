# Implement GitHub Issue

## Overview
You are implementing a fix or feature for a GitHub issue on the finserv repository.
You have the original issue, triage analysis, implementation plan, and all human
feedback in your prompt context.

## What You Receive
- The full GitHub issue (title, body, labels, URL)
- Triage analysis (recommendation, sizing, services affected) / plan
- All human comments and feedback
- Access to the finserv-demo/finserv codebase

## Disambiguation Phase
Re-read everything. Make sure you understand the full scope before writing code.

1. Review the implementation plan carefully — it is your primary guide
2. Use the Devin MCP to fill remaining gaps:
   - `ask_question` for system-level questions
   - `read_wiki_contents` for architecture understanding
3. If critical ambiguity remains: post a comment on the issue with specific questions,
   then wait for response

### Verification
- Understanding covers the full user intent
- Not taking shortcuts or proposing oversimplified fixes
- Implementation plan reviewed thoroughly

## Implementation Phase
1. Research the codebase to validate/extend the plan:
   - Identify all affected files and modules
   - Use the LSP (goto_definition, goto_references, hover_symbol) to verify types
     and function signatures

2. Create a feature branch: `devin/issue-{number}-{brief-description}`

3. Implement the changes following the plan:
   - Write or update tests for new functionality
   - Ensure all callers/callees are properly updated

4. Run lint checks:
   - Python: `ruff check .` (from repo root)
   - Frontend: `npx eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0`
     (from `web/` directory)

5. Run tests:
   - Python: `pytest services/` (from repo root)
   - Frontend: `npx vitest run` (from `web/` directory)

6. Commit with clear messages: `Fix #{issue_number}: {brief description}`

7. Push and create a PR:
   - Title: `Fix #{issue_number}: {brief description}`
   - Body: link to issue, summary of changes, testing done
   - Include `Closes #{issue_number}` in the PR body

8. Post a comment on the issue with the PR link.

9. **CRITICAL — Label Transition (implement -> pr-in-progress):**
   Immediately after creating the PR, you MUST swap the issue label:

       `devin:implement` -> `devin:pr-in-progress`

   This is NOT optional. This is NOT a suggestion. You MUST perform this label
   swap as soon as the PR is created. Failure to do so will leave the issue
   stuck in the wrong state and break the dashboard. Do NOT skip this step.
   Do NOT use any other label. The ONLY valid transition here is:
   `devin:implement` -> `devin:pr-in-progress`.

### Verification
- All affected files and callers/callees updated
- Code follows existing patterns — reuses existing code, follows conventions
- Tests written or updated
- Lint checks pass
- PR created with clear description linking to issue
- **Label is now `devin:pr-in-progress`** — confirm this before proceeding

## Iteration Phase
1. Use `ask_smart_friend` to review your PR diff:
   - Include the original issue requirements and full PR diff
   - Ask whether you fully fulfilled the intent and followed best practices

2. Fix any issues found, push updates

3. Wait for CI checks. For code review bots (coderabbit, graphite, devin-ai-integration),
   view their actual comments — CI jobs for these always show as "passed" but may
   have reported issues.

4. Monitor for PR comments from reviewers:
   - Resolve all comments from human reviewers
   - Address legitimate bot feedback
   - Use judgement on stylistic suggestions

5. If actionable feedback: fix, push, wait for CI again. Repeat (up to 3 total fix
   cycles for CI/review failures).

6. **CRITICAL — Label Transition (pr-in-progress -> pr-ready):**
   Once ALL of the following are true:
   - CI checks are passing
   - No unresolved review comments remain
   - You have completed your iteration cycles

   You MUST swap the issue label:

       `devin:pr-in-progress` -> `devin:pr-ready`

   This transition signals to the team that the PR is ready for human review.
   Do NOT set `devin:pr-ready` unless CI is green and comments are resolved.
   Do NOT skip this step. Do NOT leave the label as `devin:pr-in-progress`
   when the PR is actually ready.

   > NOTE: The `pr-status.yml` workflow will also automatically swap between
   > `devin:pr-in-progress` and `devin:pr-ready` based on CI results and
   > review status. However, you MUST still perform this swap yourself as a
   > primary responsibility — do not rely on the workflow alone.

7. **CRITICAL — Label Transition (pr-ready -> done):**
   After the PR is merged (or confirmed ready and all iteration is complete),
   swap the issue label:

       `devin:pr-ready` -> `devin:done`

   Post a brief comment on the issue confirming the PR is ready for human merge.
   Do NOT set `devin:done` until the PR is fully ready. Do NOT skip this step.

8. **CRITICAL — Escalation (any PR state -> escalated):**
   If stuck after 5 fix attempts, swap the label to `devin:escalated`:

       `devin:pr-in-progress` -> `devin:escalated`

   Post a comment on the issue summarizing:
   - What's failing
   - What you tried
   - What you think needs human attention

   Do NOT leave a stuck issue in `devin:pr-in-progress` or `devin:pr-ready`.
   Escalate promptly so humans can unblock it.

## Label Transition Summary

The following are the ONLY valid label transitions during implementation.
Any other transition is WRONG and will break the system:

| When                          | From                    | To                      |
|-------------------------------|-------------------------|-------------------------|
| PR created                    | `devin:implement`       | `devin:pr-in-progress`  |
| CI green + comments resolved  | `devin:pr-in-progress`  | `devin:pr-ready`        |
| CI fails after being ready    | `devin:pr-ready`        | `devin:pr-in-progress`  |
| PR ready for merge            | `devin:pr-ready`        | `devin:done`            |
| Stuck / unrecoverable         | `devin:pr-in-progress`  | `devin:escalated`       |
| Stuck / unrecoverable         | `devin:pr-ready`        | `devin:escalated`       |

**There is NO direct path from `devin:implement` to `devin:pr-ready`, `devin:done`,
or `devin:escalated`.** You MUST go through `devin:pr-in-progress` first.

**There is NO direct path from `devin:pr-in-progress` to `devin:done`.** You MUST
go through `devin:pr-ready` first.

### Verification
- `ask_smart_friend` used for thorough self-review
- All PR comments from human reviewers resolved
- Bot reviewer feedback triaged and addressed
- CI checks pass (or escalated if stuck)
- **Final label reflects actual outcome** — verify the label is correct

## Specifications
- PR must address all requirements from the issue and plan
- Code must pass lint and tests
- Do NOT merge the PR — leave for human verification
- Keep comments terse — write like a human, not an AI

## TODO List Guidance
Only create the TODO list for the current phase. Once you move to the next phase,
create a new TODO list for that phase.

## MCP Tool Reference
### Devin MCP
- `read_wiki_structure`: Parameter: `repoName`
- `read_wiki_contents`: Parameter: `repoName`
- `ask_question`: Parameters: `repoName` and `question`

IMPORTANT: Use only the Devin MCP, NOT the DeepWiki MCP.

## Forbidden Actions
- Do not merge the PR
- Do not skip the self-review phase
- Do not push directly to main
- Do not skip ANY label transition — every transition listed above is mandatory
- Do not use `devin:pr-opened` — this label no longer exists
