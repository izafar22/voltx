# RushX code standards

## General
Make minimal, reviewable changes consistent with nearby code. Prefer existing modules and interfaces over new frameworks. No unrelated refactoring in feature PRs. Document new configuration, migrations and operational implications.

## Backend
Python FastAPI, Pydantic, async MongoDB Motor/PyMongo patterns. Keep route handlers thin where feasible; use existing services for business rules. Validate external inputs, authorization and state transitions. Avoid network I/O inside request handlers where an outbox exists. Use explicit UTC timestamps and idempotent writes for retries. Never log OTPs, access tokens, customer phone numbers unnecessarily, webhook verification secrets or payment credentials.

## WhatsApp
Audit `backend/services/whatsapp_service.py` and `backend/templates/whatsapp_utility_catalog.json` before changing anything. Confirm exact production Meta template name, language and ordered body parameters; do not infer approval from local catalog. Honor recorded opt-in and recipient restrictions. Preserve durable outbox, deduplication, bounded retries and signed webhook validation. Test duplicate events, Meta 429/5xx, malformed payloads and status callbacks. Do not send live test messages without explicit authorization.

## Frontend
React functional components and existing styling conventions; accessible labels and keyboard behavior; responsive layouts and both themes. Reuse established API/client, route and component patterns. Avoid exposing secrets in frontend environment variables.

## Quality gates
Run applicable backend tests, frontend tests/build and Playwright checks where available. For security-sensitive changes add negative/authorization tests. Report exact commands and outcomes, including anything not run. Never claim CI or production success without evidence. Keep .env and private files out of commits.
