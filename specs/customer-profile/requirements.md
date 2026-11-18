# Customer profile and linked sign-in requirements

Version 1.0 requirements agreed with the owner on 2026-11-18.

Requirements and design are finalized and approved by the owner on 2026-11-18, including the corrected RushX branding and full repair-form navigation. See `design.md`. Implementation tasks are recorded in `tasks.md` and were authorized by the owner on 2026-11-18.

## Customer outcome

Customers can view and manage their personal details and saved addresses from the customer dashboard. Google and WhatsApp OTP can both provide access to the same customer account, including its dashboard, repairs and addresses.

## Profile details

| Field | Required behavior |
|---|---|
| Full name | Customers can view and edit their full name. |
| Email address | Supplied and verified through Google authentication. Displayed as read-only once linked. |
| Mobile number | Customers can add or change their number after verifying the new number through the existing WhatsApp OTP integration. |
| Addresses | Customers can manage multiple saved addresses for pickup and delivery. |

Only verified email addresses and mobile numbers can be added through these profile flows.

## Google and WhatsApp account linking

1. A customer signed in through WhatsApp OTP can add an email through a clearly labelled Connect Google account flow.
2. That flow requires successful Google authentication and a Google-verified email before saving the email and linking the Google identity.
3. A customer signed in through Google can add a mobile number through WhatsApp OTP verification. Successful verification links that number to the same customer account and enables WhatsApp sign-in.
4. Once both methods are linked, either method opens the same account and its existing dashboard, repair history and saved addresses.
5. Changing a mobile number requires verification of the replacement number before the change is applied. After successful replacement, retain and refresh the current session and sign out all other existing account sessions (owner-approved on 2026-11-18).
6. The profile clearly identifies the customer's available sign-in methods and explains when adding a verified contact detail also enables another sign-in method.
7. Customers continue using their available verified sign-in method while an addition or change is pending or fails.

## Conflicts and verification failures

1. Check whether the Google identity or mobile number being linked already belongs to another RushX account.
2. Reject linking if either identity belongs to another account. Show a clear error explaining that the identity is already associated with an account.
3. Preserve the customer's current account, linked sign-in methods and data when a conflict occurs.
4. Cancelled, failed or expired verification leaves the attempted contact detail and sign-in method unlinked.

The agreed version 1.0 conflict resolution is rejection of the linking attempt.

## Saved addresses

1. Customers can add multiple addresses.
2. Customers can edit and delete their saved addresses.
3. Customers can label addresses, such as Home or Office.
4. Customers can set a default pickup address and a default delivery address.
5. Customers can select a saved address for pickup or delivery.
6. Customers manage and select addresses belonging to their own account.

## Acceptance criteria

- The customer can access their profile and saved addresses from the dashboard.
- A saved full-name edit appears in the customer's profile.
- A WhatsApp customer adding an email completes Google authentication and gains Google access to the same customer account.
- A Google customer adding a mobile number completes WhatsApp OTP verification and gains WhatsApp access to the same customer account.
- Changing a mobile number takes effect after successful WhatsApp OTP verification.
- Signing in with either linked method resolves to the same customer account and its repairs and addresses.
- A conflicting Google identity or mobile number produces a clear rejection and preserves existing account data and access.
- Failed verification preserves the current profile and sign-in methods.
- The linked Google email is read-only and Google-verified.
- Multiple address creation, editing, deletion, labelling, defaults and pickup/delivery selection work for the authenticated customer.
- The interface clearly explains available sign-in methods and the effect of linking verified details.

## Agreed delivery sequence

1. Record the finalized requirements in this document.
2. Review the design, including profile navigation, address fields, verification and linking flows, conflict messages, and default-address behavior when an address is deleted.
3. Derive implementation tasks from the approved design and review those tasks with the owner.
4. Implement the approved tasks and validate their acceptance criteria.

The owner has deferred treatment of existing data while this feature is specified. Design and task planning should focus on the new profile and linking flows.

## Implementation checkpoint

The current Google sign-in implementation identifies users by Google subject in `backend/google_oidc.py` and refreshes verified Google email metadata during sign-in. The dashboard is implemented in `frontend/src/pages/customer/CustomerHome.jsx`. Inspect the actual auth routes, WhatsApp OTP behavior and related tests during design.

This document records the requested behavior. Implementation status is tracked in `context/progress-tracker.md`.
