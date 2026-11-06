import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { FEATURES } from './config/features';
const defaults = { ...FEATURES };
let mockUser, mockLoading;
const mockChargingMount = jest.fn();
// Jest 27 does not resolve this package's exports map. Resolve its CJS entry to
// exercise the installed, real router (including browser history and redirects).
jest.mock('react-router-dom', () => {
  global.TextEncoder = require('util').TextEncoder;
  global.TextDecoder = require('util').TextDecoder;
  const path = require('path');
  const fs = require('fs');
  const domDirectory = path.dirname(require.resolve('react-router-dom/package.json'));
  // npm may nest react-router under react-router-dom or hoist it.
  const entry = [path.join(domDirectory, 'node_modules/react-router/dist/development/index.js'), path.join(domDirectory, '../react-router/dist/development/index.js')].find(file => fs.existsSync(file));
  return require(entry);
}, { virtual: true });
jest.mock('@/App.css', () => ({}), { virtual: true });
jest.mock('@/context/ThemeContext', () => ({ ThemeProvider: ({ children }) => children, useTheme: () => ({ theme: "light", toggle: jest.fn() }) }), { virtual: true });
jest.mock('@/context/AuthContext', () => ({ AuthProvider: ({ children }) => children, useAuth: () => ({ user: mockUser, loading: mockLoading }) }), { virtual: true });
jest.mock('./context/AuthContext', () => ({ useAuth: () => ({ user: mockUser, loading: mockLoading }) }));
jest.mock('@/components/ui/sonner', () => ({ Toaster: () => null }), { virtual: true });
jest.mock('@/components/ProtectedRoute', () => require('./components/ProtectedRoute'), { virtual: true });
jest.mock('@/pages/Login', () => () => <p>Login screen</p>, { virtual: true });
jest.mock('@/pages/customer/CustomerHome', () => () => <p>Customer dashboard</p>, { virtual: true });
jest.mock('@/pages/customer/ChargerPage', () => () => { mockChargingMount(); return <p>Charger page</p>; }, { virtual: true });
jest.mock('@/pages/customer/LivePage', () => () => { mockChargingMount(); return <p>Live page</p>; }, { virtual: true });
jest.mock('@/pages/customer/WalletPage', () => () => { mockChargingMount(); return <p>Wallet page</p>; }, { virtual: true });
jest.mock('@/pages/customer/HistoryPage', () => () => { mockChargingMount(); return <p>History page</p>; }, { virtual: true });
jest.mock('@/pages/customer/RepairNew', () => () => <p>Existing repair form</p>, { virtual: true });
jest.mock('@/pages/customer/RepairDetail', () => () => <p>Existing repair detail</p>, { virtual: true });
jest.mock('@/pages/customer/RepairsList', () => () => <p>Existing repair list</p>, { virtual: true });
jest.mock('@/pages/owner/OwnerDashboard', () => () => <p>Owner console</p>, { virtual: true });
jest.mock('@/pages/admin/AdminDashboard', () => () => <p>Admin console</p>, { virtual: true });
jest.mock('@/pages/admin/RepairAdmin', () => () => <p>Repair administration</p>, { virtual: true });
let container, root;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true; jest.clearAllMocks(); Object.assign(FEATURES, defaults);
  window.scrollTo = jest.fn(); sessionStorage.clear();
  mockUser = { role: 'customer' }; mockLoading = false;
  container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); container.remove(); Object.assign(FEATURES, defaults); });
const mount = async path => { window.history.replaceState({}, '', path); await act(async () => root.render(<App />)); };
test.each(['/app/wallet', '/app/history', '/app/charger/IND000001', '/app/live/session-1'])('disabled route %s redirects without mounting charging page', async path => {
  await mount(path); expect(window.location.pathname).toBe('/app'); expect(container.textContent).toContain('Customer dashboard'); expect(mockChargingMount).not.toHaveBeenCalled();
});
test.each([['/repairs', 'list'], ['/repairs/new', 'form'], ['/repairs/r1', 'detail']])('authenticated repair route %s stays available', async (path, page) => {
  await mount(path); expect(window.location.pathname).toBe(path); expect(container.textContent).toContain(`Existing repair ${page}`);
});
test.each(['/app', '/repairs/new', '/repairs/r1', '/app/charger/IND000001'])('unauthenticated %s still requires login', async path => {
  mockUser = null; await mount(path); expect(window.location.pathname).toBe('/login'); expect(mockChargingMount).not.toHaveBeenCalled();
});
test('session loading does not prematurely redirect', async () => {
  mockUser = null; mockLoading = true; await mount('/repairs/new'); expect(window.location.pathname).toBe('/repairs/new'); expect(container.textContent).not.toContain('Existing repair form');
});
test.each([['/app/wallet', 'wallet'], ['/app/history', 'charging'], ['/app/charger/IND000001', 'charging'], ['/app/live/s1', 'charging']])('enabled route %s renders preserved page', async (path, feature) => {
  FEATURES[feature] = true; await mount(path); expect(window.location.pathname).toBe(path); expect(mockChargingMount).toHaveBeenCalled();
});
test.each([['owner', '/owner', '/app', 'Customer dashboard'], ['admin', '/admin', '/admin/repairs', 'Repair administration']])('%s legacy console redirects to active RushX release page', async (role, path, destination, content) => {
  mockUser = { role }; await mount(path); expect(window.location.pathname).toBe(destination); expect(container.textContent).toContain(content);
  expect(container.textContent).not.toContain('Owner console');
  expect(container.textContent).not.toContain('Admin console');
});
test.each([['customer', '/app'], ['owner', '/app']])('%s cannot access an admin console', async (role, destination) => {
  mockUser = { role }; await mount('/admin'); expect(window.location.pathname).toBe(destination); expect(container.textContent).not.toContain('Admin console');
});
test('admin can access repair administration directly', async () => {
  mockUser = { role: 'admin' }; await mount('/admin/repairs'); expect(container.textContent).toContain('Repair administration');
});
test.each(['customer', 'owner'])('%s cannot access repair administration', async role => {
  mockUser = { role }; await mount('/admin/repairs'); expect(window.location.pathname).toBe('/app'); expect(container.textContent).not.toContain('Repair administration');
});
test('owner retains access to own repair routes without access to network console', async () => {
  mockUser = { role: 'owner' }; await mount('/repairs'); expect(container.textContent).toContain('Existing repair list');
});
test('signed-out admin route requires login', async () => {
  mockUser = null; await mount('/admin'); expect(window.location.pathname).toBe('/login'); expect(container.textContent).not.toContain('Admin console');
});

test.each(['/', '/services', '/about', '/how-it-works', '/faq'])('public page %s renders without a session', async path => {
  mockUser = null; await mount(path); expect(window.location.pathname).toBe(path);
  expect(container.querySelector('h1')).not.toBeNull();
  expect(container.textContent).toContain('Independent, multi-brand service');
  expect(document.querySelector('link[rel="canonical"]').href).toBe('https://evchargerrepair.in' + path);
  expect(container.querySelector('a[href="/repairs/new"]')).not.toBeNull();
});
test('repair destination is retained at the existing login boundary', async () => {
  mockUser = null; await mount('/repairs/new');
  expect(sessionStorage.getItem('rushx.repair-destination')).toBe('/repairs/new');
});
