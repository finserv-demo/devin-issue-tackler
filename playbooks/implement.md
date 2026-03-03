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

9. Swap label: `devin:implement` → `devin:pr-opened`

### Verification
- All affected files and callers/callees updated
- Code follows existing patterns — reuses existing code, follows conventions
- Tests written or updated
- Lint checks pass
- PR created with clear description linking to issue

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

6. **If all clean after iteration**: swap label `devin:pr-opened` → `devin:done`.
   Post a brief comment on the issue confirming the PR is ready for human merge.

7. **If stuck after 5 fix attempts**: swap label `devin:pr-opened` → `devin:escalated`.
   Post a comment on the issue summarizing:
   - What's failing
   - What you tried
   - What you think needs human attention

### Verification
- `ask_smart_friend` used for thorough self-review
- All PR comments from human reviewers resolved
- Bot reviewer feedback triaged and addressed
- CI checks pass (or escalated if stuck)
- Final label reflects outcome (done or escalated)

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
