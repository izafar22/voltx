# Public customer education browser checks

Run `npm run build` in `frontend`, then `npm ci`, `npx playwright install chromium`, and `npm test` in this directory. Node 22 is used in CI. This isolated package avoids changing the application's dependency locks.

The suite serves only the local production build on 127.0.0.1:3100, mocks authentication APIs, and blocks external requests. It never connects to MongoDB, sends an OTP or contacts Google. Screenshots therefore exercise the site's system-font fallback as well as its layout. Screenshot and failure artifacts are written to ignored `test-results` and uploaded by CI.

Coverage: all five public pages, metadata, no horizontal overflow, mobile menu and Escape focus, keyboard FAQ, service anchors, repair CTA login handoff, mocked SMS completion and a simulated existing Google callback session at 320, 375, 768 and 1280px.

Real Google authentication, SMS delivery and server-side repair submission remain staging checks; browser mocks do not establish provider or production configuration correctness.
