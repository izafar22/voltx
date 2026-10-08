# Repair MVP release boundary

Verified on branch `repair-mvp` on 2026-10-08. The working tree was clean before this task. This is dashboard/release-boundary preparation, not a full repair production-readiness audit.

## Release switches

`src/config/features.js` is the central frontend configuration. These switches control UI and mounting, not authorization; backend permissions remain authoritative.

| Switch | MVP value | Behavior |
| --- | --- | --- |
| repair | true | Repair dashboard, navigation, creation/list/detail routes |
| charging | false | Master switch for customer station-code entry, sessions/history and charging routes |
| qrCharging | false | Existing QR/manual-code dialog; also requires charging |
| stationDiscovery | false | Station summary/query; also requires charging |
| stationMap | false | Map mounting; also requires charging and stationDiscovery |
| wallet | false | Wallet card, query and route; independent of charging |

To restore the complete preserved charging dashboard, enable charging, qrCharging, stationDiscovery, stationMap and wallet, then rebuild. QR remains its existing manual-code fallback; this task adds no camera scanner. Owner/admin console routes are unchanged.

With the MVP defaults, `/stations`, `/sessions` and `/wallet` queries are disabled. The map is not mounted, so it requests neither tiles nor geolocation. Charging/wallet notifications are hidden and their `/notifications` polling is stopped: the current backend produces only charging/wallet events. Revisit this condition when repair notifications are implemented. Direct customer wallet/history/charger/live URLs redirect to `/app` without mounting the disabled page. Authentication still runs before the feature redirect.

## Repair experience

The primary CTA opens `/repairs/new`. The dashboard displays up to six recent requests, in the API's newest-first order, with existing status labels and links to `/repairs/:id`. View all repairs opens `/repairs`.

The dashboard and history share `useMyRepairs`, `/api/repairs?scope=mine`, and the existing `repairs-mine` query cache. Both provide loading, empty and retryable error states. Creation invalidates that cache after submission so returning to the dashboard does not retain a stale list. Existing detail-page status actions already invalidate the same key.

Customer desktop/mobile navigation shows Home and Repairs, with logout and theme controls retained. Sign-in marketing copy follows the release flags; no sign-in logic changed.

No backend, authentication provider, cookie/session architecture, OTP behavior, CORS/Origin middleware, `/api` client configuration, or setupProxy changes were made.

## Files changed

- `src/config/features.js`: centralized release switches (new).
- `src/App.js`: gated customer routes; auth and owner/admin routing retained.
- `src/components/layout/CustomerShell.jsx`: navigation/notification gating, touch targets, repair-route active state.
- `src/pages/customer/CustomerHome.jsx`: primary repair CTA, summary mounting, charging UI/query gating.
- `src/pages/customer/CustomerHome.css`: repair layout, responsive spacing and keyboard focus.
- `src/components/RepairOverview.jsx`: recent repair summary and data states (new).
- `src/hooks/useMyRepairs.js`: shared existing scoped query (new).
- `src/lib/repairStatus.js`: existing list status labels extracted for reuse (new).
- `src/pages/customer/RepairsList.jsx`: shared hook/labels and retryable errors.
- `src/pages/customer/RepairNew.jsx`: invalidate repair history after successful creation.
- `src/pages/Login.jsx`: release-aware marketing copy only.
- `src/App.test.jsx`: real-router route/role/auth guard tests with page stubs (new).
- `src/pages/customer/CustomerHome.mvp.test.jsx`: real React Query tests for repair states, navigation and API suppression/restoration (new).
- `src/pages/customer/CustomerHome.test.jsx`: retained charging coverage with flags enabled.
- `src/components/layout/CustomerShell.test.jsx`: mobile/desktop nav gating, notifications and logout.
- `src/pages/customer/RepairNew.test.jsx`: creation cache invalidation.
- `src/pages/Login.test.jsx`: release-aware copy, preserving existing auth tests.
- `REPAIR_MVP.md`: this release and verification record.

## Verification

- `CI=true npm test -- --watch=false --runInBand`: 9 suites, 120 tests passed.
- `npm run build`: compiled successfully.
- `git diff --check`: passed.
- Tests cover primary CTA, list/detail links, loading/empty/error+retry states, six-item summary, suppressed charging requests even with cached charging data, independently enabled wallet, restored charging controls/queries, hidden mobile navigation, preserved logout, unauthenticated routing, session loading, role restrictions, disabled route redirects, and enabled route restoration.
- Browser used the existing localhost development server and its demo customer OTP flow; real existing repair data loaded. No repair was created or modified during manual checks.
- Manually verified login → dashboard → existing repair form, mobile Repairs → history → detail, dashboard summary → detail, disabled wallet URL → dashboard, and logout → repair-focused sign-in.
- Visually inspected dashboard at 1440px, 768px, 375px and 320px. Document scroll width matched viewport width at all four sizes. Inspected light/dark themes, mobile drawer, prominent 48px-high repair CTA and visible keyboard focus.
- Browser coverage uses development auth, not a production SMS provider. API suppression is asserted by React Query/API-spy tests; no browser network interception was used.

## Findings deferred to the repair audit

1. Ordinary customers cannot retrieve/select registered chargers: RepairNew returns an empty list for their role. Owner/admin users call `/owner/chargers`, whose backend requires those roles and filters by owner_id. The default Other charger flow and basic navigation remain available. Ownership semantics need a separate review; no permission checks were relaxed.
2. An existing cancelled repair detail still displays generic instructions to ship the charger to Voltx. That pre-existing lifecycle copy should be corrected during the repair audit.

No dashboard-specific blocker was found in these checks. These findings and the complete repair lifecycle still require the planned audit before claiming the full repair module is production-ready.
