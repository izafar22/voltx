import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import CustomerHome from './CustomerHome';
import { FEATURES } from '../../config/features';
const defaults = { ...FEATURES };
const mockGet = jest.fn(), mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({ useNavigate: () => mockNavigate }), { virtual: true });
jest.mock('../../lib/api', () => ({ api: { get: (...args) => mockGet(...args) }, inr: value => `₹${value}` }));
jest.mock('../../context/AuthContext', () => ({ useAuth: () => ({ user: { name: 'Asha' } }) }));
jest.mock('../../components/layout/CustomerShell', () => ({ CustomerShell: ({ children }) => <main>{children}</main> }));
jest.mock('../../components/StationsMap', () => ({ StationsMap: () => <div data-testid="map" /> }));
jest.mock('../../components/ui/button', () => ({ Button: ({ children, variant, size, ...props }) => <button {...props}>{children}</button> }));
jest.mock('../../components/ui/input', () => ({ Input: props => <input {...props} /> }));
jest.mock('../../components/ui/dialog', () => ({ Dialog: ({ children }) => <div>{children}</div>, DialogTrigger: ({ children }) => children, DialogContent: () => null, DialogHeader: () => null, DialogTitle: () => null, DialogDescription: () => null }));
let root, container, client;
const repairs = [{ id: 'r1', repair_request_number: 'VOLTX-001', status: 'AWAITING_SHIPMENT', charger_info: { brand: 'ABB', model: 'Terra' } }];
const settle = () => act(async () => { await new Promise(resolve => setTimeout(resolve, 10)); });
const mount = async () => { await act(async () => root.render(<QueryClientProvider client={client}><CustomerHome /></QueryClientProvider>)); await settle(); };
const click = selector => act(() => container.querySelector(selector).click());
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true; jest.clearAllMocks(); Object.assign(FEATURES, defaults);
  client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
  mockGet.mockImplementation(path => Promise.resolve({ data: path === '/repairs' ? repairs : path === '/wallet' ? { balance: 100 } : [] }));
  container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); client.clear(); container.remove(); Object.assign(FEATURES, defaults); });
test('repair MVP loads scoped requests only and links to existing creation, list and detail routes', async () => {
  await mount();
  expect(container.textContent).toContain('Repair a Charger');
  expect(container.textContent).toContain('My Repair Requests');
  expect(container.textContent).toContain('VOLTX-001'); expect(container.textContent).toContain('ABB · Terra'); expect(container.textContent).toContain('Awaiting shipment');
  expect(mockGet.mock.calls).toEqual([['/repairs', { params: { scope: 'mine' } }]]);
  click('[data-testid="repair-charger-btn"]'); expect(mockNavigate).toHaveBeenLastCalledWith('/repairs/new');
  click('[data-testid="view-all-repairs"]'); expect(mockNavigate).toHaveBeenLastCalledWith('/repairs');
  click('[data-testid="dashboard-repair-r1"]'); expect(mockNavigate).toHaveBeenLastCalledWith('/repairs/r1');
});
test('disabled charging features stay hidden even with cached charging data', async () => {
  client.setQueryData(['sessions'], [{ session_id: 's1', status: 'active' }]);
  client.setQueryData(['wallet'], { balance: 500 });
  await mount();
  for (const text of ['Scan QR', 'Enter station code', 'Loaded station status', 'Recent charging', 'Charging in progress', 'Nearby charging stations', 'Wallet balance']) expect(container.textContent).not.toContain(text);
  expect(container.querySelector('[data-testid="map"]')).toBeNull();
  expect(container.querySelector('.dashboard-grid')).toBeNull();
  expect(mockGet.mock.calls.map(call => call[0])).toEqual(['/repairs']);
});
test('empty state remains actionable', async () => {
  mockGet.mockResolvedValue({ data: [] }); await mount();
  expect(container.textContent).toContain('No repair requests yet');
  click('[data-testid="repair-charger-btn"]'); expect(mockNavigate).toHaveBeenCalledWith('/repairs/new');
});
test('pending repairs show loading without blocking the CTA', async () => {
  mockGet.mockImplementation(() => new Promise(() => {})); await mount();
  expect(container.querySelector('[role="status"]').textContent).toContain('Loading repair requests');
  expect(container.querySelector('[data-testid="repair-charger-btn"]').disabled).toBe(false);
});
test('API failure has a safe error and retry recovers', async () => {
  mockGet.mockRejectedValueOnce(new Error('private server detail')); await mount();
  expect(container.querySelector('[role="alert"]').textContent).toContain('Unable to load repair requests');
  expect(container.textContent).not.toContain('private server detail');
  await act(async () => container.querySelector('[role="alert"] button').click()); await settle();
  expect(container.querySelector('[role="alert"]')).toBeNull(); expect(container.textContent).toContain('VOLTX-001');
});
test('summary limits recent results to six while preserving view all', async () => {
  mockGet.mockResolvedValue({ data: Array.from({ length: 9 }, (_, i) => ({ ...repairs[0], id: `r${i}` })) });
  await mount(); expect(container.querySelectorAll('[data-testid^="dashboard-repair-"]')).toHaveLength(6);
  expect(container.querySelector('[data-testid="view-all-repairs"]')).not.toBeNull();
});
test('enabling charging restores preserved controls and queries', async () => {
  Object.keys(FEATURES).forEach(key => { FEATURES[key] = true; }); await mount();
  expect(container.querySelector('[data-testid="map"]')).not.toBeNull();
  expect(container.textContent).toContain('Scan QR'); expect(container.textContent).toContain('Enter station code');
  expect(container.textContent).toContain('Loaded station status'); expect(container.textContent).toContain('Recent charging');
  expect(mockGet.mock.calls.map(call => call[0]).sort()).toEqual(['/repairs', '/sessions', '/stations', '/wallet']);
});
test('charging alone does not enable discovery, QR or wallet queries', async () => {
  FEATURES.charging = true; await mount();
  expect(container.querySelector('[data-testid="map"]')).toBeNull(); expect(container.textContent).not.toContain('Scan QR');
  expect(mockGet.mock.calls.map(call => call[0]).sort()).toEqual(['/repairs', '/sessions']);
});
test('wallet can be enabled independently without fetching stations or sessions', async () => {
  FEATURES.wallet = true; await mount();
  expect(container.querySelector('[data-testid="wallet-card"]')).not.toBeNull();
  expect(mockGet.mock.calls.map(call => call[0]).sort()).toEqual(['/repairs', '/wallet']);
});
