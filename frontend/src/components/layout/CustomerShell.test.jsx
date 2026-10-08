import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CustomerShell } from './CustomerShell';
jest.mock('react-router-dom', () => ({ Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a>, useLocation: () => ({ pathname: '/app' }), useNavigate: () => jest.fn() }), { virtual: true });
jest.mock('@/lib/api', () => ({ api: { get: () => Promise.resolve({ data: [] }) } }), { virtual: true });
jest.mock('@/context/AuthContext', () => ({ useAuth: () => ({ user: { name: 'Customer', role: 'customer' }, logout: jest.fn() }) }), { virtual: true });
jest.mock('@/context/ThemeContext', () => ({ useTheme: () => ({ theme: 'light', toggle: jest.fn() }) }), { virtual: true });
jest.mock('@/components/Logo', () => ({ Logo: () => <span>Voltx</span> }), { virtual: true });
jest.mock('@/components/ui/sheet', () => require('../ui/sheet'), { virtual: true });
jest.mock('@/components/ui/badge', () => ({ Badge: ({ children }) => <span>{children}</span> }), { virtual: true });
jest.mock('@/lib/utils', () => ({ cn: (...classes) => classes.filter(Boolean).join(' ') }), { virtual: true });
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
    expect(drawer.textContent).toContain('Voltx');
    act(() => drawer.querySelector('[data-testid="nav-home"]').click());
    expect(menu.getAttribute('aria-expanded')).toBe('false');
  } finally { act(() => root.unmount()); container.remove(); }
});
