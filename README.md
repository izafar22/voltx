# Here are your Instructions

RushX WhatsApp setup, templates, worker operations and testing: [backend/WHATSAPP.md](backend/WHATSAPP.md). The integration defaults to disabled.

### Prelaunch MongoDB bootstrap and Google admin access

See [the production bootstrap runbook](backend/PRODUCTION_BOOTSTRAP.md) for the versioned, idempotent index CLI, verified Google first-login enrollment and operator-only admin promotion, required manual Render database switch, smoke checks and rollback. These commands require explicit operator approval/execution; no production migration or deployment is performed automatically.
