# WhatsApp estimate decisions — task plan

Status: WED-01 through WED-07 IMPLEMENTED AND LOCALLY VALIDATED on 2026-11-21; review and external activation gates remain.

| ID | Deliverable | Acceptance evidence |
|---|---|---|
| DONE WED-01 | Exact actionable estimate, decline-ack and positive-balance QR template catalogs with independent gates/readiness | Contract/manifest/QR negatives; feature-off compatibility |
| DONE WED-02 | Compact signed, expiring action payloads bound to repair/estimate/destination | Tamper, expiry, cross-repair/recipient and secret-absence tests |
| DONE WED-03 | Signed webhook parsing and deduplicated durable action inbox | Signature, size, sender, malformed/duplicate/unsupported callback tests |
| DONE WED-04 | Worker lease, current-state revalidation and atomic estimate decision CAS | Crash/retry, duplicate, conflict, pause/phone/consent/status races |
| DONE WED-05 | Shared web/WhatsApp decision audit contract and acknowledgement outbox | Same status semantics; exactly one history/audit/acknowledgement |
| DONE WED-06 | Metrics/readiness/runbook and safe redaction | Aggregate outcomes only; no raw tokens/phones/bodies |
| DONE WED-06A | Reviewed QR URL validation and positive-balance image-header serialization | Exact asset/template only; text fallback; zero-balance/payment-received isolation |
| DONE WED-07 | Backend/lifecycle regressions and context updates | Exact commands/results in validation.md; diff/secret review |
| WED-08 | PR review and CI | Owner-approved merge only after green exact-head checks |
| WED-09 | Meta audit/submission and staging acceptance | Separately authorized; real button callbacks and receipts |
| WED-10 | Selected production release | Separately approved artifact, activation and rollback |

Implementation order is WED-01 through WED-07 after approval. WED-08 through WED-10 remain separate authorization gates.
