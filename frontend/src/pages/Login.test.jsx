import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import Login from './Login';
import { FEATURES } from '../config/features';
const mockPost = jest.fn(), mockLogin = jest.fn(), mockNavigate = jest.fn();
let mockAuth;
jest.mock('../lib/api', () => ({ api: { post: (...args) => mockPost(...args) } }));
jest.mock('../context/AuthContext', () => ({ useAuth: () => mockAuth }));
jest.mock('../components/ProtectedRoute', () => ({ homeFor: role => role === 'admin' ? '/admin' : role === 'owner' ? '/owner' : '/app' }));
jest.mock('react-router-dom', () => ({ useNavigate: () => mockNavigate, Navigate: ({ to }) => <span data-redirect={to} />, Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a> }), { virtual: true });
jest.mock('@/context/ThemeContext', () => ({ useTheme: () => ({ theme: 'light', toggle: jest.fn() }) }), { virtual: true });
jest.mock('../components/Logo', () => ({ Logo: () => <span>RushX</span> }));
jest.mock('../components/ui/button', () => ({ Button: ({ children, variant, ...props }) => <button {...props}>{children}</button> }));
jest.mock('../components/ui/input', () => ({ Input: props => <input {...props} /> }));
let root, container;
const originalDemo = process.env.REACT_APP_DEMO_AUTH;
beforeEach(() => {
  sessionStorage.clear();
  process.env.REACT_APP_DEMO_AUTH = "false";
  global.IS_REACT_ACT_ENVIRONMENT = true; jest.clearAllMocks();
  mockAuth = { user: null, loading: false, login: mockLogin };
  container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); container.remove(); jest.useRealTimers(); process.env.REACT_APP_DEMO_AUTH = originalDemo; });
const render = () => act(() => root.render(<Login />));
const fill = (id, value) => act(() => { const input = container.querySelector('#' + id); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value); input.dispatchEvent(new Event('input', { bubbles: true })); });
const submit = async () => act(async () => { container.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); });
async function request() {
  mockPost.mockResolvedValueOnce({ data: { challenge_id: 'challenge', expires_in: 300, resend_after: 60 } });
  render(); fill('phone', '98765 43210'); await submit();
}
async function registration() {
  await request(); mockPost.mockResolvedValueOnce({ data: { registration_required: true, registration_token: 'scoped-test-grant' } });
  fill('otp', '123456'); await submit();
}
test('phone screen has no name or demo controls by default', () => {
  render(); expect(container.querySelector('#phone')).not.toBeNull(); expect(container.querySelector('#full-name')).toBeNull();
  expect(container.textContent).not.toContain('demo');
});
test('normalizes phone and masks OTP destination', async () => {
  await request(); expect(mockPost).toHaveBeenCalledWith('/auth/request-otp', { phone: '+919876543210' });
  expect(container.textContent).toContain('+91••••••3210'); expect(container.textContent).not.toContain('+919876543210');
});
test('existing user verifies then enters dashboard', async () => {
  await request(); const user = { name: 'Returning', role: 'customer' }; mockPost.mockResolvedValueOnce({ data: { user, authenticated: true } });
  fill('otp', '123456'); await submit();
  expect(mockPost).toHaveBeenLastCalledWith('/auth/verify-otp', { phone: '+919876543210', challenge_id: 'challenge', otp: '123456' });
  expect(mockLogin).toHaveBeenCalledWith(user); expect(mockNavigate).toHaveBeenCalledWith('/app', { replace: true });
});
test('new user requires name and optional email validation before registration', async () => {
  await registration(); expect(container.textContent).toContain('Your number has been verified');
  fill('full-name', '  '); await submit(); expect(container.textContent).toContain('Enter your full name');
  fill('full-name', ' Asha Sharma '); fill('email', 'bad'); await submit(); expect(container.textContent).toContain('Enter a valid email');
  fill('email', 'asha@example.com'); mockPost.mockResolvedValueOnce({ data: { user: { name: 'Asha Sharma', role: 'customer' } } });
  await submit(); expect(mockPost).toHaveBeenLastCalledWith('/auth/register-customer', { name: 'Asha Sharma', email: 'asha@example.com' }, { headers: { Authorization: 'Bearer scoped-test-grant' } });
  expect(mockNavigate).toHaveBeenCalledWith('/app', { replace: true });
});
test('resend waits for server countdown and then requests a fresh challenge', async () => {
  jest.useFakeTimers(); await request();
  expect([...container.querySelectorAll('button')].find(b => b.textContent === 'Resend in 60s').disabled).toBe(true);
  act(() => jest.advanceTimersByTime(60000));
  const resend = [...container.querySelectorAll('button')].find(b => b.textContent === 'Resend code'); expect(resend.disabled).toBe(false);
  mockPost.mockResolvedValueOnce({ data: { challenge_id: 'next', resend_after: 60 } }); await act(async () => resend.click());
  expect(mockPost).toHaveBeenCalledTimes(2);
});
test.each([400, 429])('invalid/expired/limited OTP %s leaves user unauthenticated', async status => {
  await request(); mockPost.mockRejectedValueOnce({ response: { status, data: { detail: 'internal diagnostic' } } }); fill('otp','000000'); await submit();
  expect(container.querySelector('[role="alert"]')).not.toBeNull(); expect(container.textContent).not.toContain('internal diagnostic'); expect(mockLogin).not.toHaveBeenCalled();
});
test.each([['customer','/app'],['owner','/owner'],['admin','/admin']])('authenticated %s leaves login', (role, path) => {
  mockAuth.user = { role }; render(); expect(container.querySelector('[data-redirect]').getAttribute('data-redirect')).toBe(path);
});
test('duplicate OTP submissions are locked while in flight', async () => {
  await request(); let resolve; mockPost.mockImplementationOnce(() => new Promise(r => { resolve = r; })); fill('otp','123456');
  await submit(); await submit(); expect(mockPost).toHaveBeenCalledTimes(2);
  await act(async () => resolve({ data: { user: { role:'customer' } } }));
});

test('explicit demo controls are available only in nonproduction builds', () => {
  process.env.REACT_APP_DEMO_AUTH = 'true'; render();
  expect(container.textContent).toContain('Development demo accounts');
});

test('repair release sign-in copy preserves the charging copy behind its flag', () => {
  act(() => root.render(<Login />));
  expect(container.textContent).toContain('Repair when possible.');
  expect(container.textContent).not.toContain('Find your next charge');
  const previous = FEATURES.charging;
  try {
    FEATURES.charging = true; act(() => root.render(<Login />));
    expect(container.textContent).toContain('Find your next charge');
  } finally { FEATURES.charging = previous; }
});

test('dual login uses top-level Google navigation', () => {
  const originalLocation = window.location;
  const assign = jest.fn();
  delete window.location;
  window.location = { assign, search: '' };
  render();
  const google = [...container.querySelectorAll('button')].find(button => button.textContent === 'Continue with Google');
  expect(google).toBeDefined();
  act(() => google.click());
  expect(assign).toHaveBeenCalledWith('/api/auth/google/login');
  expect(mockPost).not.toHaveBeenCalled();
  window.location = originalLocation;
});

test('Google callback failure shows a clear error and keeps SMS available', () => {
  window.history.replaceState({}, '', '/login?google_error=1');
  render();
  expect(container.querySelector('[role="alert"]').textContent).toContain('Google sign-in could not be completed');
  expect(container.querySelector('#phone')).not.toBeNull();
  window.history.replaceState({}, '', '/login');
});

test('OTP success returns to the pending repair request', async () => {
  sessionStorage.setItem('rushx.repair-destination', '/repairs/new');
  await request(); mockPost.mockResolvedValueOnce({ data: { user: { role: 'customer' } } });
  fill('otp', '123456'); await submit();
  expect(mockNavigate).toHaveBeenCalledWith('/repairs/new', { replace: true });
});
test('authenticated Google return resumes the pending repair request', () => {
  sessionStorage.setItem('rushx.repair-destination', '/repairs/new'); mockAuth.user = { role: 'customer' }; render();
  expect(container.querySelector('[data-redirect]').getAttribute('data-redirect')).toBe('/repairs/new');
});
test('untrusted stored destination cannot redirect outside the app', () => {
  sessionStorage.setItem('rushx.repair-destination', 'https://example.com'); mockAuth.user = { role: 'customer' }; render();
  expect(container.querySelector('[data-redirect]').getAttribute('data-redirect')).toBe('/app');
});

test('Google return keeps the saved destination under React Strict Mode', () => {
  sessionStorage.setItem('rushx.repair-destination', '/repairs/new'); mockAuth.user = { role: 'customer' };
  act(() => root.render(<React.StrictMode><Login /></React.StrictMode>));
  expect(container.querySelector('[data-redirect]').getAttribute('data-redirect')).toBe('/repairs/new');
});

test('login offers public navigation and the shared theme toggle without unsupported repair promises', () => {
  render(); expect(container.querySelector('a[href="/"]')).not.toBeNull();
  expect(container.querySelector('[aria-label="Switch to dark theme"]')).not.toBeNull();
  expect(container.textContent).not.toMatch(/of any brand|every model/i);
});
