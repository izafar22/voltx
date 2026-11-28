# RushX — Architecture memory and discussion capture

Status: PROPOSED (documentation-only draft; no workflow automation is installed).

## Purpose
Preserve architectural decisions from ChatGPT/Codex discussions across sessions without confusing an idea, approval, implemented code or deployed production state.

## Authority and reading order
- `AGENTS.md` and the six `context/` files remain the agent entrypoint.
- `docs/RUSHX_PROJECT_STATE.md` is a dated handover, not live production proof.
- Accepted ADRs in `docs/adr/` will record architectural intent. Source code, GitHub PRs and verified operator evidence remain authoritative for implementation and deployment claims.
- `repair-mvp` is the integration baseline; changes go through reviewed PRs. Release and production promotion require separate approval.

## Proposed capture flow
1. After a substantial architectural discussion, ChatGPT prepares a structured **draft proposal** on a `docs/<topic>` branch from the latest verified `repair-mvp`.
2. Each proposal states: discussion date/source, problem, proposed decision, alternatives, trade-offs, assumptions, affected components, risks, open questions, and approval status.
3. User reviews and explicitly approves or requests changes. Only after approved merge may the proposal be marked **ACCEPTED**; do not treat a draft PR as an accepted decision.
4. New sessions read accepted ADRs plus the six context files and verify branch, current PRs, deployment SHA and runtime claims independently.
5. Superseded ADRs link to their replacement. No silent overwrites; unresolved conflicts are surfaced.

## Template
```markdown
# ADR-XXXX: <title>
Status: PROPOSED | ACCEPTED | SUPERSEDED
Date: YYYY-MM-DD
Source: <discussion reference or UNKNOWN>
Decision owner: human reviewer

## Context
## Decision proposed
## Alternatives considered
## Consequences and risks
## Implementation evidence (or NOT IMPLEMENTED)
## Production evidence (or NOT DEPLOYED)
## Open questions
## Approval / supersession references
```

## RushX-specific safeguards
- Do not publish customer details, OTPs, credentials, payment data, WhatsApp recipients or internal host secrets.
- Never imply WhatsApp template approval, live worker status, payment readiness, legal ownership or actual repair facilities without verified evidence.
- No change to FastAPI/React, database, CI/CD, production, staging, Meta, DNS or releases from this documentation proposal.
- No background conversation capture is active. Draft creation requires an explicit request or a separately approved integration; every draft and merge requires review.

## Cold-start acceptance
A new ChatGPT session and a new Codex session must identify the same accepted decisions, outstanding proposals, active integration baseline, and authorization gates from repository evidence alone. Stale snapshots must be labelled stale.

## Initial proposal
Pilot the draft-after-substantial-discussion workflow on the next RushX architecture decision, then evaluate whether to implement automated draft creation via an explicitly connected workflow.
