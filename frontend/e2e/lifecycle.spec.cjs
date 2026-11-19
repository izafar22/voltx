const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

async function fixture(page, theme, role = 'customer', verified = true) {
  let user = { user_id: 'synthetic-customer', role, name: 'Example Customer', phone: verified ? '+919876543210' : '',
    phone_verified: verified, google_linked: true, email: 'customer@example.com', status: 'active' };
  let repair = { id: 'lifecycle-test', repair_request_number: 'TEST-10421', user_id: user.user_id,
    customer_type: 'RETAIL', status: 'REQUESTED', charger_info: { brand: 'Test brand', charger_type: 'AC' },
    problem_description: 'Synthetic fault', photos: [], created_at: '2026-11-20T00:00:00Z',
    status_history: [], whatsapp_updates: { state: 'enabled', destination: '••42', can_stop: true },
    intake_preview: { address: 'Synthetic intake address (not for dispatch)', digest: 'a'.repeat(64) } };
  const sent = [];
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(theme => localStorage.setItem('rushx-theme', theme), theme);
  await page.route('**/api/**', async route => {
    const request = route.request(), path = new URL(request.url()).pathname;
    const body = request.postDataJSON();
    if (path === '/api/auth/me') return route.fulfill({ json: user });
    if (path === '/api/customer/profile') return route.fulfill({ json: { user, addresses: [], revision: 0, pickup_id: null, delivery_id: null } });
    if (path === '/api/customer/whatsapp-capability') return route.fulfill({ json: { available: !!user.phone_verified,
      reason_code: user.phone_verified ? 'ready' : 'verify_phone', destination: '••42', identity_key: 'synthetic-identity', binding: 'synthetic-binding' } });
    if (path === '/api/auth/link/phone/request') return route.fulfill({ json: { challenge_id: 'synthetic-challenge', resend_after: 60 } });
    if (path === '/api/auth/link/phone/verify') { user = { ...user, phone: '+919876543210', phone_verified: true }; return route.fulfill({ json: { user } }); }
    if (path === '/api/repairs' && request.method() === 'POST') { sent.push({ path, body }); return route.fulfill({ json: repair }); }
    if (path === '/api/repairs') return route.fulfill({ json: [repair] });
    if (path === '/api/repairs/lifecycle-test/status') {
      sent.push({ path, body }); repair = { ...repair, status: body.status, intake_acceptance: { address: repair.intake_preview.address, at: '2026-11-20T00:00:00Z' } };
      return route.fulfill({ json: repair });
    }
    if (path === '/api/repairs/lifecycle-test/whatsapp-consent') {
      repair = { ...repair, whatsapp_updates: { state: 'stopped', can_stop: false } }; return route.fulfill({ json: { ok: true } });
    }
    if (path === '/api/repairs/lifecycle-test') return route.fulfill({ json: repair });
    if (path === '/api/admin/summary') return route.fulfill({ json: {} });
    if (path === '/api/admin/users') return route.fulfill({ json: [user] });
    return route.fulfill({ json: [] });
  });
  return { sent, errors };
}

for (const theme of ['light', 'dark']) {
  test(`lifecycle opt-in, requested confirmation and withdrawal ${theme}`, async ({ page }) => {
    const data = await fixture(page, theme);
    await page.goto('/repairs/new');
    await page.getByTestId('brand-input').fill('Test brand');
    await page.getByTestId('description-input').fill('Synthetic charging fault');
    await page.getByTestId('type-select').click();
    await page.getByRole('option', { name: 'AC Charger', exact: true }).click();
    const consent = page.getByRole('checkbox', { name: 'Send me WhatsApp updates about this repair' });
    await expect(consent).toBeEnabled(); await expect(consent).not.toBeChecked();
    await consent.check();
    const violations = await new AxeBuilder({ page }).include('section[aria-label="WhatsApp repair updates"]').withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
    expect(violations.violations).toEqual([]);
    await page.getByTestId('submit-repair-btn').click();
    await expect(page.getByTestId('repair-confirmation')).toBeVisible();
    await expect(page.getByText(/Please do not ship your charger yet/)).toBeVisible();
    expect(data.sent).toHaveLength(1); expect(data.sent[0].body.whatsapp_opt_in).toBe(true); expect(data.sent[0].body.whatsapp_binding).toBe('synthetic-binding');
    await page.getByTestId('view-repair-btn').click();
    await expect(page.getByText(/Wait for RushX to review your request/)).toBeVisible();
    await page.getByRole('button', { name: 'Stop WhatsApp updates', exact: true }).click();
    await page.getByRole('button', { name: 'Stop updates', exact: true }).click();
    await expect(page.getByText('WhatsApp updates are stopped for this repair. Follow progress here.')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(data.errors).toEqual([]);
  });

  test(`lifecycle phone verification preserves repair draft ${theme}`, async ({ page }) => {
    const data = await fixture(page, theme, 'customer', false);
    await page.goto('/repairs/new');
    await page.getByTestId('brand-input').fill('Draft brand');
    await page.getByTestId('description-input').fill('Preserve this synthetic draft');
    await page.getByTestId('type-select').click();
    await page.getByRole('option', { name: 'AC Charger', exact: true }).click();
    await page.getByRole('button', { name: 'Verify mobile for updates' }).click();
    await page.getByLabel('Mobile number', { exact: true }).fill('9876543210');
    await page.getByRole('button', { name: 'Send WhatsApp code' }).click();
    await page.getByLabel('WhatsApp verification code').fill('123456');
    await page.getByRole('button', { name: 'Verify and connect', exact: true }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    expect(data.sent).toEqual([]); // Portal verification submits must not create the repair.
    await expect(page.getByTestId('brand-input')).toHaveValue('Draft brand');
    await expect(page.getByTestId('description-input')).toHaveValue('Preserve this synthetic draft');
    await expect(page.getByRole('checkbox', { name: 'Send me WhatsApp updates about this repair' })).toBeEnabled();
    expect(data.errors).toEqual([]);
  });

  test(`lifecycle admin confirms intake instructions ${theme}`, async ({ page }) => {
    const data = await fixture(page, theme, 'admin');
    await page.goto('/admin');
    if (await page.getByTestId('menu-btn').isVisible()) await page.getByTestId('menu-btn').click();
    await page.locator('[data-testid="side-repairs"]:visible').click();
    await page.getByTestId('repair-row-lifecycle-test').click();
    await page.getByTestId('status-action-AWAITING_SHIPMENT').click();
    const panel = page.locator('section[aria-label="Accept for inspection"]');
    await expect(panel.getByRole('button', { name: 'Accept and provide shipping instructions' })).toBeDisabled();
    await panel.getByRole('checkbox').check();
    await panel.getByRole('button', { name: 'Accept and provide shipping instructions' }).click();
    await expect(page.getByTestId('repair-detail-status')).toHaveText('Awaiting shipment');
    expect(data.sent[0].body.acceptance).toEqual({ confirmed: true, preview_digest: 'a'.repeat(64) });
    expect(data.errors).toEqual([]);
  });
}

for (const theme of ['light', 'dark']) {
  test(`withdrawal confirmation resets when navigating between repairs ${theme}`, async ({ page }) => {
    await fixture(page, theme);
    await page.route('**/api/repairs/lifecycle-second', route => route.fulfill({ json: {
      id: 'lifecycle-second', repair_request_number: 'TEST-SECOND', status: 'REQUESTED',
      charger_info: { brand: 'Second charger' }, status_history: [], created_at: '2026-11-20T00:00:00Z',
      whatsapp_updates: { state: 'enabled', destination: '••42', can_stop: true }
    } }));
    await page.goto('/repairs/lifecycle-test');
    await page.getByRole('button', { name: 'Stop WhatsApp updates', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Stop updates', exact: true })).toBeVisible();
    await page.evaluate(() => {
      history.pushState({}, '', '/repairs/lifecycle-second');
      dispatchEvent(new PopStateEvent('popstate'));
    });
    await expect(page.getByTestId('detail-number')).toHaveText('TEST-SECOND');
    await expect(page.getByRole('button', { name: 'Stop updates', exact: true })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Stop WhatsApp updates', exact: true })).toBeVisible();
  });
}
