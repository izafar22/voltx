import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import CustomerHome from './CustomerHome';
const mockNavigate = jest.fn();
const mockGet = jest.fn();
let mockQueries;
jest.mock('react-router-dom', () => ({ useNavigate: () => mockNavigate }), { virtual: true });
jest.mock('@tanstack/react-query', () => ({ useQuery: ({ queryKey }) => mockQueries[queryKey[0]] }));
jest.mock('../../lib/api', () => ({ api: { get: (...args) => mockGet(...args) }, inr: (value) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(value) }));
jest.mock('../../context/AuthContext', () => ({ useAuth: () => ({ user: { name: 'Asha' } }) }));
jest.mock('../../components/layout/CustomerShell', () => ({ CustomerShell: ({ children }) => <main>{children}</main> }));
jest.mock('../../components/StationsMap', () => ({ StationsMap: ({ stations }) => <div data-testid="map">{stations.map(s => <span key={s.charger_id}>{s.name}</span>)}</div> }));
jest.mock('../../components/ui/button', () => ({ Button: ({ children, variant, size, ...props }) => <button {...props}>{children}</button> }));
jest.mock('../../components/ui/input', () => ({ Input: (props) => <input {...props} /> }));
jest.mock('../../components/ui/dialog', () => ({ Dialog: ({ children }) => <div>{children}</div>, DialogTrigger: ({ children }) => children, DialogContent: () => null, DialogHeader: () => null, DialogTitle: () => null, DialogDescription: () => null }));
let root, container;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.clearAllMocks();
  mockQueries = Object.fromEntries(['wallet', 'stations', 'sessions'].map(key => [key, { data: key === 'wallet' ? { balance: 14640 } : [], isPending: false, isError: false, refetch: jest.fn() }]));
  container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); container.remove(); });
const render = () => act(() => root.render(<CustomerHome />));
const inputCode = (code) => act(() => {
  const input = container.querySelector('[data-testid="station-code-input"]');
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, code);
  input.dispatchEvent(new Event('input', { bubbles: true }));
});
const submit = () => container.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
test('normal data renders wallet, stations, shared status counts and mobile-first map order', () => {
  mockQueries.stations.data = ['Available', 'Charging', 'Preparing', 'Finishing', 'Fault', 'Offline', 'Unknown'].map((status, i) => ({ charger_id: String(i), name: `Station ${i}`, status }));
  render();
  expect(container.textContent).toContain('Asha');
  expect(container.textContent).toContain('₹14,640.00');
  expect(container.textContent).toContain('Station 0');
  expect(container.textContent).toContain('1 available in loaded stations');
  expect([...container.querySelectorAll('dd')].map(el => el.textContent)).toEqual(['1', '3', '3', '7']);
  expect(container.querySelector('.dashboard-grid').firstElementChild.className).toContain('dashboard-map');
});
test.each([['wallet', 'Loading wallet'], ['stations', 'Loading charging stations'], ['sessions', 'Loading recent charging']])('%s loading is independent', (key, label) => {
  mockQueries[key].isPending = true; mockQueries[key].data = undefined; render();
  expect(container.querySelector(`[aria-label="${label}"]`)).not.toBeNull();
  expect(container.querySelector('[data-testid="repair-charger-btn"]')).not.toBeNull();
});
test.each([['wallet', 'Unable to load wallet balance'], ['stations', 'Unable to load charging stations'], ['sessions', 'Unable to load recent charging']])('%s errors have independent retry', (key, message) => {
  mockQueries[key].isError = true; render();
  const error = [...container.querySelectorAll('[role="alert"]')].find(el => el.textContent.includes(message));
  expect(error).toBeDefined(); act(() => error.querySelector('button').click());
  expect(mockQueries[key].refetch).toHaveBeenCalledTimes(1);
  expect(container.querySelector('[data-testid="map"]')).not.toBeNull();
});
test('empty recent sessions and malformed wallet value are safe', () => {
  mockQueries.wallet.data.balance = NaN; render();
  expect(container.textContent).toContain('No charging sessions yet');
  expect(container.querySelector('[data-testid="wallet-balance"]').textContent).toBe('—');
});
test('recent sessions include time, energy, price and status', () => {
  mockQueries.sessions.data = [{ session_id: '1', charger_name: 'City Center', start_time: '2026-09-14T10:00:00Z', energy_kwh: 4.25, cost: 63.75, status: 'completed' }]; render();
  expect(container.textContent).toContain('City Center'); expect(container.textContent).toContain('4.25 kWh'); expect(container.textContent).toContain('₹63.75');
});
test('blank station code disables submit', () => {
  render(); inputCode('   '); expect(container.querySelector('[data-testid="code-go-btn"]').disabled).toBe(true);
  act(() => submit()); expect(mockGet).not.toHaveBeenCalled();
});
test('station form trims code, prevents duplicate submission, and navigates', async () => {
  let finish; mockGet.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  render(); inputCode('  ind000001  ');
  act(() => { submit(); submit(); });
  expect(mockGet).toHaveBeenCalledTimes(1); expect(mockGet).toHaveBeenCalledWith('/chargers/IND000001');
  expect(container.querySelector('[data-testid="code-go-btn"]').disabled).toBe(true);
  await act(async () => finish({ data: {} }));
  expect(mockNavigate).toHaveBeenCalledWith('/app/charger/IND000001');
});
test('invalid code shows inline safe error and permits retry', async () => {
  mockGet.mockRejectedValue({ response: { status: 404, data: { detail: 'private diagnostic' } } }); render(); inputCode('invalid');
  await act(async () => submit());
  expect(container.textContent).toContain('Station code not found'); expect(container.textContent).not.toContain('private diagnostic');
  expect(container.querySelector('[data-testid="code-go-btn"]').disabled).toBe(false);
});
