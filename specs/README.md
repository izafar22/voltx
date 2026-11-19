# RushX specifications

Store each spec in `specs/<spec-name>/`, using a descriptive lowercase name with hyphens, such as `customer-profile`.

Each spec contains:

- `requirements.md`: scope, customer behavior, acceptance criteria and requirement approvals.
- `design.md`: user experience, technical design, decisions and design approvals. If a separate design is unnecessary, record that decision here.
- `tasks.md`: ordered implementation tasks, dependencies, validation checks and progress.

Finalize requirements first, then review the design where needed, then prepare and review implementation tasks before implementing them. Record approval dates and keep task status consistent with actual evidence. Link to these documents from context and PRs rather than keeping duplicate copies in `docs/`.

## Specs

| Spec | Requirements | Design | Tasks |
|---|---|---|---|
| WhatsApp lifecycle updates (design review) | [Requirements](whatsapp-lifecycle-updates/requirements.md) | [Design proposal](whatsapp-lifecycle-updates/design.md) | [Workflow gates](whatsapp-lifecycle-updates/tasks.md) |
| Customer profile | [Requirements](customer-profile/requirements.md) | [Design](customer-profile/design.md) | [Tasks](customer-profile/tasks.md) |

Earlier specifications and operational references in `docs/` retain their existing locations until deliberately reorganized. New specs follow this structure.
