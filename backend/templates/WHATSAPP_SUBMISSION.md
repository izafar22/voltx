# Meta Utility template submission and manual verification

This is a submission artifact, **not a submission or approval record**. Do not
submit, edit an in-review template, send live messages, activate production or
register/migrate any number without explicit human authorization. Template names
are proposed; verify any existing templates first. Language is exactly `en_US`.
All samples below are fictional, not actual personal data or shipping instructions.
Replace them with business-approved nonpersonal samples when preparing submission.

## Checklist — status as of this implementation

We have not inspected Meta Business Manager or production configuration. The JSON
catalog's proposed names and this environment example do not mean anything is
configured in a live account. Record verified dates/evidence in restricted operations
records, not credentials or recipient details in this repository.

| Event / template | Configured | Submitted | Approved | Pending | Blocked |
| --- | --- | --- | --- | --- | --- |
| REQUESTED / `rushx_repair_requested_v1` | unknown | unknown | unknown | unknown | unknown |
| AWAITING_SHIPMENT / `rushx_awaiting_shipment_v1` | unknown | unknown | unknown | unknown | unknown |
| RECEIVED_AT_VOLTX / `rushx_charger_received_v1` | unknown | unknown | unknown | unknown | unknown |
| ESTIMATE_SENT / `rushx_estimate_ready_v1` | unknown | unknown | unknown | unknown | unknown |
| CUSTOMER_APPROVED / `rushx_estimate_approved_v1` | unknown | unknown | unknown | unknown | unknown |
| REPAIR_COMPLETED / `rushx_repair_completed_v1` | unknown | unknown | unknown | unknown | unknown |
| PAYMENT_PENDING / `rushx_payment_pending_v1` | unknown | unknown | unknown | unknown | unknown |
| SHIPPED_TO_CUSTOMER / `rushx_return_shipped_v1` | unknown | unknown | unknown | unknown | unknown |

## Prepare and submit (human-controlled)

1. In the correct Meta Business account and WhatsApp Manager, inspect existing
   templates by exact name and language. Record their actual category, body,
   variable order and review state. **Leave every in-review template unchanged.**
   If its copy differs, document that difference for review before changing code
   or submitting a separate version. Do not assume names in this catalog exist.
2. For an authorized remaining template, choose category **Utility** and English
   (US), name exactly as below, and positional body variables. The integration
   sends body text only: do not add header/button variables requiring extra inputs.
3. Paste the exact body and provide each positional sample in order. Preview its
   rendered text. Proposed Issue #3 copy is preserved verbatim; no policy-related
   copy deviations have been made in this implementation.
4. Submit only with explicit authorization and record the resulting review state.
   Meta can reject, reclassify or suspend templates; code cannot guarantee Utility
   classification or approval. Resolve provider feedback through human review.
5. Once approved, recheck the exact name, `en_US`, Utility category, body and order
   in the intended account. Configure that entry in WHATSAPP_TEMPLATES_JSON and
   set its approval_status to approved only after verification. Pending/unknown
   entries must remain blocked. Production requires all eight verified entries.

## Exact bodies and variable order

### 1. rushx_repair_requested_v1

Event: `REQUESTED` · Language: `en_US` · Requested category: `UTILITY`

```text
Hello {{1}}, your RushX repair request {{2}} has been received for your {{3}} charger. We will share the next steps shortly.
```

| Position | Snapshot field | Fictional example |
| --- | --- | --- |
| {{1}} | `customer_name` | Sample Customer |
| {{2}} | `repair_number` | REP-10421 |
| {{3}} | `charger_description` | ExampleBrand AC 7.4 kW |

### 2. rushx_awaiting_shipment_v1

Event: `AWAITING_SHIPMENT` · Language: `en_US` · Requested category: `UTILITY`

```text
Hello {{1}}, repair {{2}} is ready for dispatch. Please securely package your charger and send it to: {{3}}. Keep your courier tracking details.
```

| Position | Snapshot field | Fictional example |
| --- | --- | --- |
| {{1}} | `customer_name` | Sample Customer |
| {{2}} | `repair_number` | REP-10421 |
| {{3}} | `dispatch_address` | Sample Service Centre, Unit 12, Example Industrial Estate (fictional; replace before submission) |

### 3. rushx_charger_received_v1

Event: `RECEIVED_AT_VOLTX` · Language: `en_US` · Requested category: `UTILITY`

```text
Hello {{1}}, we have received your charger for repair {{2}}. Our technical team will inspect it and update you when the estimate is ready.
```

| Position | Snapshot field | Fictional example |
| --- | --- | --- |
| {{1}} | `customer_name` | Sample Customer |
| {{2}} | `repair_number` | REP-10421 |

### 4. rushx_estimate_ready_v1

Event: `ESTIMATE_SENT` · Language: `en_US` · Requested category: `UTILITY`

```text
Hello {{1}}, the repair estimate for {{2}} is ready. Estimated total: INR {{3}}. Please review and approve or decline it in your RushX dashboard.
```

| Position | Snapshot field | Fictional example |
| --- | --- | --- |
| {{1}} | `customer_name` | Sample Customer |
| {{2}} | `repair_number` | REP-10421 |
| {{3}} | `estimate_total` | 2750.00 |

### 5. rushx_estimate_approved_v1

Event: `CUSTOMER_APPROVED` · Language: `en_US` · Requested category: `UTILITY`

```text
Hello {{1}}, your approval for repair {{2}} has been recorded. Our team will proceed with the repair.
```

| Position | Snapshot field | Fictional example |
| --- | --- | --- |
| {{1}} | `customer_name` | Sample Customer |
| {{2}} | `repair_number` | REP-10421 |

### 6. rushx_repair_completed_v1

Event: `REPAIR_COMPLETED` · Language: `en_US` · Requested category: `UTILITY`

```text
Hello {{1}}, repair work for {{2}} has been completed. We will update you about remaining payment and return-shipment steps.
```

| Position | Snapshot field | Fictional example |
| --- | --- | --- |
| {{1}} | `customer_name` | Sample Customer |
| {{2}} | `repair_number` | REP-10421 |

### 7. rushx_payment_pending_v1

Event: `PAYMENT_PENDING` · Language: `en_US` · Requested category: `UTILITY`

```text
Hello {{1}}, repair {{2}} is awaiting payment confirmation. Amount due: INR {{3}}. Please check your RushX dashboard or contact support for payment instructions.
```

| Position | Snapshot field | Fictional example |
| --- | --- | --- |
| {{1}} | `customer_name` | Sample Customer |
| {{2}} | `repair_number` | REP-10421 |
| {{3}} | `amount_due` | 1750.00 |

### 8. rushx_return_shipped_v1

Event: `SHIPPED_TO_CUSTOMER` · Language: `en_US` · Requested category: `UTILITY`

```text
Hello {{1}}, your charger for repair {{2}} has been dispatched. Courier: {{3}}. Tracking number: {{4}}. Track using the courier official tracking service.
```

| Position | Snapshot field | Fictional example |
| --- | --- | --- |
| {{1}} | `customer_name` | Sample Customer |
| {{2}} | `repair_number` | REP-10421 |
| {{3}} | `courier` | Example Courier |
| {{4}} | `tracking_number` | SAMPLE123456 |

## Eight-event smoke test (do not run autonomously)

Prerequisites: explicit live-test approval, an isolated test database/app, Meta's
test sender ID, an explicitly authorized and opted-in test recipient, all required
business facts and approved templates. Keep WHATSAPP_MODE=test and the production
approval flag false. Enable and start the worker only for the approved test window.
Never use or migrate the existing personal Business App number.

1. Submit a new repair with explicit opt-in. REQUESTED must contain the actual
   account name, new repair number and submitted brand/model; inspect one job.
2. Advance to AWAITING_SHIPMENT (the existing UI does this after creation). Confirm
   the actual configured dispatch address appears. Distinguish the customer's
   inbound dispatch instructions from a return-shipment claim.
3. Move through IN_TRANSIT_TO_VOLTX to RECEIVED_AT_VOLTX as an admin. Only receipt
   sends at this step. DIAGNOSING itself must not notify.
4. Save/edit a real test estimate while it is draft: **no message**. Publish using
   ESTIMATE_SENT. Verify the published total, two decimal places and INR wording.
5. As the test customer, approve the valid published estimate. CUSTOMER_APPROVED
   sends once. Repeat the action: rejected transition, no duplicate event.
6. Advance through REPAIRING to REPAIR_COMPLETED. Confirm the completion message
   does not claim payment collection, a return date or a shipping carrier.
7. In the admin balance form, reconcile confirmed payments and save the actual
   remaining positive test amount. Saving alone does not notify. Advance to
   PAYMENT_PENDING and verify that exact amount, with no fabricated payment URL.
8. Advance to READY_TO_SHIP. Save actual authorized test courier/tracking details
   as admin; saving alone does not notify. Advance to SHIPPED_TO_CUSTOMER and
   verify the persisted values. Do not claim a courier booking occurred in code.

For each event record the job's opaque ID, provider message ID and receipt state
in restricted test records. Compare the actual customer-visible message with the
approved body and parameters, then verify signed delivered/read callbacks.
HTTP acceptance alone is not proof of delivery. Do not put recipient details or
screenshots containing personal data in the PR.

Repeat negative cases with mocks wherever possible: no opt-in; withdrawn consent;
missing name/address/estimate/amount/courier; malformed configuration; unsupported
status; duplicate transitions; invalid signature; 429/5xx; process restart and
ambiguous acknowledgement. Stop the test worker and disable the flag afterwards.
The sandbox hello_world template can check transport but does not validate any
of these eight Utility templates or their content.

## Remaining manual dependencies

- Meta approval/classification and exact eight-template configuration: unknown.
- Production sender/coexistence decision and protected number onboarding: manual;
  never modify the current Business App number to unblock testing.
- Real facility address, verified final balances and courier operations: business inputs.
- Real payment gateway/repair payment ledger: absent; this release records manual reconciliation only.
- Public HTTPS callback, Meta messages subscription, secrets, monitoring and least privilege: operations review.
- Production activation and any live test sends: explicit human approval required.

Official references: [Meta template message API](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/messages/template/),
[Meta-maintained Cloud API reference](https://www.postman.com/meta/whatsapp-business-platform/documentation/wlk6lh4/whatsapp-cloud-api),
[Meta WhatsApp documentation](https://developers.facebook.com/documentation/business-messaging/whatsapp/overview).
Use current WhatsApp Manager review results as the authority for actual approval.
