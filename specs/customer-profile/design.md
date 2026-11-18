# Customer profile design

Design finalized and approved by the owner on 2026-11-18 after correcting the preview's RushX branding and repair-form navigation. Requirements remain recorded in `requirements.md`. Next prepare implementation tasks for owner review before implementation.

## Navigation and page structure

Add Profile to the existing customer sidebar and mobile navigation. Route it to `/app/profile`, using CustomerShell and the current design-system components, spacing, typography, light/dark themes and focus styles.

Reuse the Logo component with its green lightning icon and foreground-colored RushX wordmark. In this reviewed flow, the Repairs action opens the full Repair a charger form at `/repairs/new`. The form retains charger selection, charger details, problem description, photos and review/submit sections. The proposed optional pickup/delivery selectors appear within that form.

Add a compact profile summary below the dashboard greeting. Show the verified email and mobile when available and a Manage profile action. When a method is missing, offer its specific connection action from the profile page.

The profile page has three sections in this order:

1. Personal details with full name and a Save name action.
2. Contact and sign-in with Google email, WhatsApp number, verification status and actions.
3. Saved addresses with defaults, Add address and per-address actions.

Each section saves independently and reports its own pending, success and error states. On narrow screens, fields and actions stack.

## Visual system

Use `frontend/src/design-system/tokens.css` and the existing Tailwind mappings as the visual source of truth. Implementation reuses CustomerShell, Button, Input, Card, Dialog, Sheet and Select where applicable.

Use Manrope for body text and Outfit for headings, neutral application and card surfaces, existing green brand/verification accents, the current primary/outline action variants, 44-pixel controls, and canonical card and control radii. Customer navigation follows the existing desktop sidebar and mobile drawer.

The initial interaction preview used a greener palette and simplified navigation. Its styling was corrected during owner review to reflect the canonical tokens, typography, control sizing and desktop sidebar. Component-level parity will be checked in Storybook and against the existing customer repair form during implementation, including light/dark themes and mobile widths.

## Contact and sign-in states

| Current account | Google row | WhatsApp row |
|---|---|---|
| Google linked | Read-only verified email | Add and verify mobile number |
| WhatsApp linked | Connect Google account | Verified mobile with Change number |
| Both linked | Read-only verified email | Verified mobile with Change number |

Place a sign-in summary immediately below the contact rows. Examples are “You can sign in with Google” and “You can sign in with Google or WhatsApp OTP.”

Google connection copy is “Verify your email with Google. You can then sign in with Google or your WhatsApp number.”

Mobile connection copy is “Verify this number through WhatsApp. You can then use it for repair contact and sign-in.”

## Link Google

1. The customer starts Connect Google account from an authenticated profile page.
2. Explain that this connects Google to their existing RushX account, then navigate to Google.
3. Bind the OAuth transaction to its purpose, initiating session and customer user_id. Retain the existing state, nonce, browser binding and PKCE checks.
4. The callback verifies the Google identity and verified email, then checks ownership.
5. If the identity belongs to the current customer, return a successful already-connected result.
6. If it belongs to another account, return to Profile with “This Google account is already linked to another RushX account. Choose a different Google account.”
7. Otherwise attach the identity to the signed-in customer and return to Profile with the verified email and updated sign-in summary.

The linking callback must resolve against the initiating customer. Expired or changed initiating sessions require a fresh attempt. Cancellation returns to Profile with a retry action.

Keep normal Google login and authenticated linking as distinct transaction purposes. Normal login continues finding accounts through their Google subject.

## Add or change a mobile number

Use a two-step dialog, full-width on small screens.

1. Enter a mobile number using the existing Indian-number normalization. Explain that WhatsApp will deliver the code.
2. Enter the six-digit code, with Verify and connect, resend countdown and Change number actions.

Reuse the current OTP provider, delivery restrictions, attempt limits and expiration behavior. Bind the challenge to its linking purpose, initiating session, customer and replacement number.

After verification, check ownership and save the number atomically. A number already belonging to this customer is an idempotent success. A number belonging to another account produces “This mobile number is already linked to another RushX account. Use a different number.”

A replacement becomes active after successful verification and ownership checks. Until then, the existing number remains the active sign-in number. On success, the sign-in summary reflects the replacement. Refresh the current session and invalidate other existing account sessions after a number change.

The authenticated linking flow must handle the verified challenge without invoking the normal login/registration branch that selects another user by phone.

## Saved addresses

### Proposed address form

| Field | Behavior |
|---|---|
| Label | Required, such as Home or Office |
| Address line 1 | Required, flat/building and street |
| Address line 2 or landmark | Optional |
| City | Required |
| State | Required |
| PIN code | Required, six digits |
| Country | India for this version, matching the current mobile and service context |
| Default pickup | Optional checkbox |
| Default delivery | Optional checkbox |

Use the profile name and verified mobile as the customer's contact details. This version's address form stores location details.

Render addresses as compact summaries with Edit, Delete, Set default pickup and Set default delivery actions. One address can be the default for both purposes.

For the first address, explicitly preselect both default checkboxes and allow the customer to change them. For later addresses, default checkboxes begin clear.

Deleting an address opens a confirmation. If it is a default, let the customer select a replacement or explicitly clear that default before confirming. Address and default-reference updates are atomic.

### Pickup and delivery selection

Add an Addresses section to the repair request form with independent pickup and delivery selectors. Prefill the customer's corresponding defaults.

Each selector offers saved addresses, Add an address and Choose later. For this design, address selection is optional at initial repair enquiry.

When creating a request, the server verifies address ownership and copies the selected address details into the repair record as snapshots. Later edits or deletion of a saved address preserve those request snapshots. Changing logistics on an existing repair remains governed by that repair's workflow.

## Data and API proposal

Preserve the existing customer user_id as the account key. Repairs and saved addresses reference that same key regardless of sign-in method.

Reuse existing unique identity fields on users:

- Full name in `name`.
- Verified mobile in `phone`, with verification timestamp.
- Google identity in `auth_provider=google` and `auth_subject`.
- Verified Google email and the existing Google verification metadata.

The current unique phone and provider/subject indexes enforce ownership. Linking uses atomic conditional writes and handles duplicate-key races as conflicts. Apply a customer-role check to the new self-service linking operations.

Persist addresses in MongoDB in one customer profile document keyed by user_id, with an address array, default pickup/delivery IDs and a revision. Use conditional updates on that revision to prevent concurrent edits from losing address changes or creating invalid default references. The interaction preview simulates saving; durable storage is part of the implementation.

Proposed authenticated endpoints:

| Operation | Endpoint |
|---|---|
| Read profile, methods and addresses | GET /api/customer/profile |
| Save full name | PATCH /api/customer/profile |
| Start Google linking | POST /api/auth/link/google/start |
| Complete Google OAuth | Existing Google callback with a server-stored transaction purpose |
| Request mobile linking code | POST /api/auth/link/phone/request |
| Verify and link mobile | POST /api/auth/link/phone/verify |
| Add address | POST /api/customer/addresses |
| Edit address | PATCH /api/customer/addresses/{id} |
| Delete address and resolve defaults | DELETE /api/customer/addresses/{id} |
| Change default references | PATCH /api/customer/address-defaults |

Profile writes accept explicitly allowed fields. Identity attachment requires its corresponding verification flow. Apply existing authentication, browser-origin protections and rate limits to the new operations. API error codes distinguish identity conflicts, expired verification, provider unavailability, validation and stale profile revisions.

## Source constraints discovered

- `GoogleOIDC.user()` currently finds or creates a user by Google subject. A linking transaction needs a purpose-specific callback path.
- `AuthService.verify()` currently finds a user by verified phone or creates a registration token. Extract the challenge-consumption logic for reuse by authenticated linking while preserving existing callers.
- `safe_user()` currently returns basic profile fields. Extend its response deliberately to communicate available sign-in methods and verified status.
- `CustomerShell` and `App.js` need the Profile navigation and protected route. The CMS SPA fallback already covers the `/app/` prefix.
- SMS wording in the current login interface should identify WhatsApp consistently when that provider is used.

## Approved design decisions

1. One Profile page with personal details, contact/sign-in and saved addresses, plus a compact dashboard summary.
2. The proposed address fields and India-only country.
3. Optional pickup/delivery address selection during initial repair enquiry, using saved defaults.
4. Explicit replacement or clearing when deleting a default address.
5. Verification dialogs and Google linking returning to Profile with clear success or conflict feedback.
6. The existing RushX lightning-mark logo and wordmark, with Repairs opening the full repair form and optional address selectors contained within it.
7. Saved addresses persist in MongoDB against the same customer account, and repair requests retain address snapshots after saved addresses change.

The owner accepted the mobile-number replacement session policy on 2026-11-18: refresh and retain the initiating session, and invalidate all other existing account sessions after successful verification and replacement.

Implementation tasks and their acceptance checks are recorded in `tasks.md` for owner review. Implementation remains pending task-plan approval.
