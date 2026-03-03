# Triage GitHub Issue

## Overview
You are triaging a GitHub issue for the finserv repository — a financial services
platform with microservices (portfolio, tax, risk-engine, market-data, onboarding,
notifications) and a React + Vite frontend.

Your job: determine if this issue should be implemented or closed, and size the effort.

## What You Receive
The full GitHub issue (title, body, labels, URL) is in your prompt context. You must have
access to the finserv-demo/finserv codebase.

## Immediate Response Phase
Do these three things FIRST, before any analysis. Speed matters — the user should see
activity within seconds of the issue being opened.

1. **Add the `devin:triage` label** to the issue.
2. **Add an eyes reaction** (👀) to the issue.
3. **Post a welcome comment** on the issue:

   ```
   I'll be triaging this issue — analyzing scope, affected services, and sizing.

   **What happens next:**
   - I'll post a triage summary with my recommendation (implement or close) and effort estimate
   - You can add context at any time by commenting on this issue

   **Commands:**
   - `/proceed` — approve implementation after triage completes
   - `/close` — close this issue and stop work
   - `/skip` — skip this issue (won't be auto-triaged again)
   ```

Only after all three are done, move to Context Gathering.

## Context Gathering Phase
Think about the full scope. Issues are sometimes sparse. Make sure you understand the
complete picture of what the user intends for a feature request, or what went wrong for
a bug.

1. Read the issue carefully — title, body, labels, any referenced PRs or issues, and attachments
2. Use the Devin MCP to understand relevant systems:
   - `ask_question` with repo "finserv-demo/finserv" for system-level questions
   - `read_wiki_contents` for architecture understanding
3. Gather additional context:
   - Search for related issues, commits, and PRs touching the same area
   - Check if the described behavior has already been addressed in recent commits
   - Look for duplicates
4. Identify scope: which services/components are involved? Bug, feature, or tech debt?

### Verification
- Affected systems and services identified
- You understand expected vs reported behavior
- Checked recent commits for existing fixes
- Searched for duplicate issues

## Analysis Phase
1. Determine relevance:
   - Already fixed by recent commits?
   - Duplicate of another issue?
   - Expected behavior?
   - Still reproducible/relevant?

2. Determine sizing (based on junior engineer effort):
   - **Small**: <2 hours. Single file or small change, one service.
   - **Medium**: 2-8 hours. Multiple files, single service, may need tests.
   - **Large**: >1 day. Multiple services, architectural changes, extensive testing.

3. Consult `ask_smart_friend`: pass in the full issue text and all gathered context.
   Ask it to evaluate your assessment and identify any gaps. Include relevant code
   snippets, file paths, and your reasoning.

4. Write your triage analysis:
   - **Summary**: What the issue is about (1-2 sentences)
   - **Recommendation**: Implement or close (with clear reasoning)
   - **Sizing**: Small/medium/large (citing the rubric)
   - **Services Affected**: Which services need changes
   - **Suggested Approach**: Brief high-level approach (2-4 sentences)

### Verification
- `ask_smart_friend` used to validate assessment
- Recommendation includes clear reasoning
- Sizing references the rubric criteria
- If recommending close, reason is specific (duplicate, already fixed, not a bug, etc.)

## Output Phase
1. Post your triage analysis as a comment on the GitHub issue. End the comment with:
   ```
   ---
   To proceed with implementation: comment `/proceed`
   To close this issue: comment `/close`
   To add context before proceeding: just comment with your input
   ```

2. Add the appropriate sizing label to the issue:
   - `devin:green`, `devin:yellow`, or `devin:red`

3. Remove the `devin:triage` label and add the `devin:triaged` label.

## Specifications
- Post triage analysis directly to the GitHub issue as a comment
- Add sizing label and swap status label (triage → triaged)
- Do NOT start any implementation or create branches/PRs
- Do NOT close the issue yourself — only recommend
- Keep comments terse — write like a human, not an AI

## TODO List Guidance
Only create the TODO list for the current phase. Once you move to the next phase,
create a new TODO list for that phase.

## MCP Tool Reference
### Devin MCP
- `read_wiki_structure`: Parameter: `repoName` (e.g., "finserv-demo/finserv")
- `read_wiki_contents`: Parameter: `repoName`
- `ask_question`: Parameters: `repoName` and `question`

IMPORTANT: Use only the Devin MCP, NOT the DeepWiki MCP.

## Forbidden Actions
- Do not start implementation or create branches/PRs
- Do not close the issue
- Do not skip the smart friend consultation
