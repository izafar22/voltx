# Staging Google login spec

Status is IN_PROGRESS. Google login, authenticated reload and the preserved repair destination are verified on 2026-11-18. Verification after an automatic staging deployment is the remaining acceptance check.

## Required outcome

Customers can use Continue with Google at `https://staging.evchargerrepair.in/login`, complete Google authentication, return to staging and establish an authenticated application session. Preserve the intended post-login destination.

## Verified checkpoint

- Staging frontend and backend were running `caadfa9f55b931dba8ec74e61dbe7902211d2208`.
- Clicking Continue with Google reached `/api/auth/google/login` and returned HTTP 503 with the message “Google sign-in is unavailable. Please use SMS or try later.”
- The operator checked the running backend, `/etc/rushx-staging/backend.env` and the previous checkout's environment files. All lacked `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` and `GOOGLE_REDIRECT_URI`.
- From `backend/`, `.venv/bin/python -m pytest tests/test_google_oidc.py -q` passed all 27 tests. Provider responses in these tests are mocked.
- The owner completed Google Cloud's required two-step verification during setup.
- Project `rushx-513416` already contains a Web application client named RushX Staging. Its existing callback targeted the historical Render staging host.
- With owner approval, the callback `https://staging.evchargerrepair.in/api/auth/google/callback` was added and verified in Google Cloud on 2026-11-18.
- The owner supplied the existing staging secret through a private local file. The three Google settings were installed in `/etc/rushx-staging/backend.env`, retaining mode 0600 and its original ownership. A private backup was retained on the VM.
- After restarting `rushx-staging.service`, `/api/` returned 200 and `/api/auth/google/login` returned 303 to Google with the expected staging client and callback.
- An invalid/cancelled callback returned 303 to `/login?google_error=1` with `Cache-Control: no-store`.
- The service still loads `/etc/rushx-staging/backend.env` alongside the CD override file.
- Real Google sign-in reached the authenticated customer dashboard at `/app`; the session survived a page reload.
- After logout, opening `/repairs/new` required login. Google sign-in with the selected test account returned to `/repairs/new`.
- Cancellation of a valid anonymous OAuth transaction and replay of the cancelled callback both returned to `/login?google_error=1`.
- Verification following an automatic staging deployment remains pending.

## Configuration and resume steps

1. Use the existing RushX Staging client in project `rushx-513416`. Its client ID is `534491246723-i0h1t8ik781ss1o5b9stk29bt0cltj85.apps.googleusercontent.com`.
2. The current staging callback is registered. Check the app audience and add the intended test account if the app is in Testing mode.
3. The existing staging secret has been installed. Keep credential files and client secrets outside Git and chat.
4. The three Google settings are in the staging service's environment file. An existing operator SSH key on the Mac was verified to provide staging admin access.
5. Service restart, health and Google redirect checks passed.
6. Real sign-in, session reload, repair destination and cancellation checks passed. After the next automatic staging deployment, verify the Google redirect and authenticated browser session again.

Google's [web server OAuth documentation](https://developers.google.com/identity/protocols/oauth2/web-server#creatingcred) describes client creation and credential storage.

## Acceptance criteria

- The login button reaches Google with the staging callback.
- An authorized test account can return to staging with a valid application session.
- The intended post-login destination is preserved.
- Cancellation or an invalid callback returns a clear login error.
- Staging credentials remain available after an automatic staging deployment.

Record the verified runtime revision and actual browser results when this work resumes.
