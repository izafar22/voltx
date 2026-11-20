# Privacy policy and data-deletion pages — requirements draft

Status: APPROVED 2026-11-20. These pages are a prerequisite for completing WhatsApp lifecycle acceptance. Approval covers the requirements and public copy; it does not authorize Meta app publication or production deployment.

## Verified need and source findings

Meta's RushX API Publish screen explicitly disables publishing until a privacy-policy URL is supplied. Its Basic settings also offer a data-deletion instructions URL. The WhatsApp setup warns that an unpublished app receives dashboard test webhooks only; live message receipt acceptance cannot be claimed from those tests.

The active site has no privacy/deletion routes or links. PublicPage.jsx owns the active public layout and footer, reusing Logo.jsx. The older components/layout/Footer.jsx contains parked product copy and placeholder contacts; it must not supply policy facts or be revived for this work. React routes must also be registered in backend/services/studio_cms.py's SPA_EXACT contract.

frontend/public/index.html loaded a legacy Emergent browser script and a PostHog initializer through an Emergent endpoint, including recording-related configuration. The owner confirmed on 2026-11-20 that this code is not required and approved its removal. The policy pages must describe the resulting implementation rather than the removed integration. Google Fonts remains loaded from Google's public font endpoints.

## Proposed customer behavior

- Public, login-free, readable pages at `/privacy-policy` and `/data-deletion`, using the existing RushX public layout, canonical logo and light/dark design tokens.
- Add both links to the active public footer and keep them accessible on mobile and by keyboard. Preserve existing login, repair, profile, estimate and payment journeys.
- Privacy copy describes actual account/verification, Google sign-in, profile/address, repair/photo/history, estimate/payment-reference, courier/tracking, WhatsApp and operational information handling. It does not describe parked charging/wallet functionality as active or invent card collection, advertising practices or retention promises.
- Distinguish WhatsApp sign-in/verification from optional repair-specific lifecycle consent. Explain stopping future updates, dashboard access, in-flight message limits and that stopping updates does not erase repair records.
- Explain relevant provider roles based on verified usage, including Google/WhatsApp, hosting/database and any retained website usage tools. Confirm manual courier/repair handling with the owner; do not invent infrastructure regions or claim India-only storage.
- Data deletion is an owner-operated request process through a confirmed, monitored business email. Explain how to identify the relevant account/repair, proportionate ownership checks, what can be removed/anonymized, and why some service/payment/security records may need retention. Do not promise an automated deletion feature, immediate erasure, an unsupported deadline or deletion from all third-party providers.
- No new deletion API, account-deletion button, database migration, retention/TTL change, bulk deletion, marketing consent flow or email sending is part of these informational pages.
- Effective/updated dates reflect the approved publication date. No placeholder contacts, unverified legal entity names or unapproved policy claims may appear on published pages.

## Owner inputs / approval gates

1. Owner supplied rushx779@gmail.com as the public business contact for both pages on 2026-11-20.
2. Owner confirmed on 2026-11-20 that the legacy Emergent/PostHog browser code is not required. Remove both runtime loaders and verify that no Emergent/PostHog request or global remains in the production build. This decision does not authorize removal of unrelated build-time visual-editing tooling.
3. The approved copy identifies the service as RushX without asserting an unverified registered legal entity. It describes provider sharing and the manual deletion process conservatively and does not promise a fixed retention or response period.
4. Requirements and public copy were approved by the owner on 2026-11-20. Design and the task plan require review before implementation under specs/README.md.
5. Preview/test the pages on staging. Production promotion/deployment and Meta app publication/callback subscription each retain their explicit, concrete approval gates. Do not publish a dummy policy URL or bypass Meta's disabled publication action.

## Acceptance criteria

- Both URLs return the actual relevant page without requiring an account, including on direct refresh; no unrelated dashboard redirect or disguised 404.
- Clear titles, headings, contact instructions, footer navigation and canonical RushX logo at 320/375/768/1280 in both themes; accessible focus and no horizontal overflow.
- Text matches implemented data handling and approved owner processes; no placeholders, secret values, personal test recipients, fabricated compliance claims or unsupported deletion promises.
- The production build contains no Emergent/PostHog runtime loader, project key, browser global or network request. Removal preserves unrelated functionality and is verified by source, build and browser checks. Retained external integrations are described accurately.
- Relevant frontend checks/build/browser checks and backend route-contract tests pass. Existing auth, OTP, repair and admin flows remain protected.
- The approved public URLs are verified before being entered into Meta; app publication and actual WhatsApp delivery remain separately evidenced.

## Deferred

General Terms of Service, refund/warranty policy redesign, automated erasure workflows, new analytics/consent-management platforms and broad legal/compliance certification are outside this first scope unless separately requested.
