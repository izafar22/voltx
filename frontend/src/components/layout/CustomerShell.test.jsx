import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CustomerShell } from './CustomerShell';
import { FEATURES } from '../../config/features';
const defaultFeatures = { ...FEATURES };
const mockGet = jest.fn(() => Promise.resolve({ data: [] }));
const mockLogout = jest.fn();
jest.mock('react-router-dom', () => ({ Link: ({ children, to, onClick, ...props }) => <a href={to} {...props} onClick={event => { event.preventDefault(); onClick?.(event); }}>{children}</a>, useLocation: () => ({ pathname: '/app' }), useNavigate: () => jest.fn() }), { virtual: true });
jest.mock('@/lib/api', () => ({ api: { get: (...args) => mockGet(...args) } }), { virtual: true });
jest.mock('@/context/AuthContext', () => ({ useAuth: () => ({ user: { name: 'Customer', role: 'customer' }, logout: mockLogout }) }), { virtual: true });
jest.mock('@/context/ThemeContext', () => ({ useTheme: () => ({ theme: 'light', toggle: jest.fn() }) }), { virtual: true });
jest.mock('@/components/Logo', () => ({ Logo: () => <span>RushX</span> }), { virtual: true });
jest.mock('@/components/ui/sheet', () => require('../ui/sheet'), { virtual: true });
jest.mock('@/components/ui/badge', () => ({ Badge: ({ children }) => <span>{children}</span> }), { virtual: true });
jest.mock('@/lib/utils', () => ({ cn: (...classes) => classes.filter(Boolean).join(' ') }), { virtual: true });
beforeEach(() => { jest.clearAllMocks(); mockGet.mockResolvedValue({ data: [] }); Object.assign(FEATURES, defaultFeatures); });
afterEach(() => Object.assign(FEATURES, defaultFeatures));
test('mobile navigation opens an accessible drawer and closes when selecting a route', async () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const container = document.createElement('div'); document.body.appendChild(container);
  const root = createRoot(container);
  try {
    await act(async () => root.render(<CustomerShell>Dashboard</CustomerShell>));
    const menu = container.querySelector('[data-testid="menu-btn"]');
    act(() => menu.click());
    expect(menu.getAttribute('aria-expanded')).toBe('true');
    const drawer = document.querySelector('[data-testid="mobile-drawer"]');
    expect(drawer.getAttribute('role')).toBe('dialog');
    expect(drawer.textContent).toContain('RushX');
    expect(drawer.querySelector('[data-testid="nav-repairs"]').getAttribute('href')).toBe('/repairs');
    expect(document.querySelector('[data-testid="nav-wallet"]')).toBeNull();
    expect(document.querySelector('[data-testid="nav-history"]')).toBeNull();
    expect(mockGet).not.toHaveBeenCalled();
    act(() => drawer.querySelector('[data-testid="nav-home"]').click());
    expect(menu.getAttribute('aria-expanded')).toBe('false');
  } finally { act(() => root.unmount()); container.remove(); }
});

test('logout stays available and enabled charging navigation/notifications return', async () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  FEATURES.charging = true; FEATURES.wallet = true;
  const container = document.createElement('div'); document.body.appendChild(container); const root = createRoot(container);
  try {
    await act(async () => root.render(<CustomerShell>Dashboard</CustomerShell>));
    expect(container.querySelector('[data-testid="nav-wallet"]').getAttribute('href')).toBe('/app/wallet');
    expect(container.querySelector('[data-testid="nav-history"]').getAttribute('href')).toBe('/app/history');
    expect(mockGet).toHaveBeenCalledWith('/notifications');
    act(() => container.querySelector('[data-testid="logout-btn"]').click());
    expect(mockLogout).toHaveBeenCalledTimes(1);
  } finally { act(() => root.unmount()); container.remove(); }
});

test('authenticated navigation offers a public-site return without replacing repair routes', () => {
  const container = document.createElement('div'); const root = createRoot(container);
  act(() => root.render(<CustomerShell><p>Dashboard content</p></CustomerShell>));
  expect(container.querySelector('a[href="/"]').textContent).toContain('Explore RushX');
  expect(container.querySelector('[data-testid="nav-repairs"]').getAttribute('href')).toBe('/repairs');
  act(() => root.unmount());
});
