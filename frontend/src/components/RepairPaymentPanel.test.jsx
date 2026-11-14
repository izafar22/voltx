import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import RepairPaymentPanel from './RepairPaymentPanel';
const mockGet = jest.fn(), mockPost = jest.fn();
jest.mock('../lib/api', () => ({ api: { get: (...args) => mockGet(...args), post: (...args) => mockPost(...args) }, inr: value => `INR ${value}` }));
let root, container;
const pending = { state: 'PENDING', amount_due: 100, receipt: {}, instructions: 'Contact RushX support', qr_image_url: null };
const change = (label, value) => act(() => {
  const node = container.querySelector(`[aria-label="${label}"]`);
  Object.getOwnPropertyDescriptor(node.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype, 'value').set.call(node, value);
  node.dispatchEvent(new Event(node.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }));
});
const submit = () => container.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
const render = async (props = {}) => { await act(async () => root.render(<RepairPaymentPanel repairId="r1" {...props} />)); };
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  Object.defineProperty(global, 'crypto', { value: { randomUUID: jest.fn(() => 'test-request-id') }, configurable: true });
  mockGet.mockReset().mockResolvedValue({ data: pending }); mockPost.mockReset();
  container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); container.remove(); });
test('text fallback and customer evidence cannot settle payment', async () => {
  await render();
  expect(container.querySelector('img')).toBeNull();
  expect(container.textContent).toContain('does not confirm payment');
  change('Transaction reference / UTR', 'UTR12345678');
  mockPost.mockResolvedValue({ data: { ok: true } });
  await act(async () => submit());
  expect(mockPost).toHaveBeenCalledWith('/repairs/r1/payment/reference', { reference: 'UTR12345678' });
  expect(container.textContent).toContain('Payment has not been confirmed');
});
test('renders configured merchant QR', async () => {
  mockGet.mockResolvedValue({ data: { ...pending, qr_image_url: 'https://merchant.example.test/qr.png' } });
  await render();
  expect(container.querySelector('img').alt).toBe('RushX merchant UPI payment QR code');
});
test('admin requires exact amount and confirmation; ambiguous retry preserves key', async () => {
  await render({ admin: true });
  change('Amount received (INR)', '100'); change('Transaction reference / UTR', 'UTR12345678');
  await act(async () => submit()); expect(mockPost).not.toHaveBeenCalled();
  act(() => container.querySelector('input[type="checkbox"]').click());
  change('Amount received (INR)', '99');
  await act(async () => submit()); expect(mockPost).not.toHaveBeenCalled();
  change('Amount received (INR)', '100');
  mockPost.mockRejectedValue(new Error('network interruption'));
  await act(async () => submit());
  await act(async () => submit());
  expect(mockPost).toHaveBeenCalledTimes(2);
  expect(mockPost.mock.calls[0]).toEqual(mockPost.mock.calls[1]);
  expect(mockPost.mock.calls[0][1]).toEqual({ amount: 100, method: 'upi', reference: 'UTR12345678', funds_received: true, idempotency_key: 'test-request-id' });
});
test('cash asks backend to generate receipt ID', async () => {
  await render({ admin: true });
  change('Amount received (INR)', '100'); change('Payment method', 'cash');
  expect(container.querySelector('[aria-label="Transaction reference / UTR"]')).toBeNull();
  act(() => container.querySelector('input[type="checkbox"]').click());
  mockPost.mockResolvedValue({ data: { ok: true } });
  await act(async () => submit());
  expect(mockPost.mock.calls[0][1].reference).toBeNull();
});
test('paid status hides collection form and QR', async () => {
  mockGet.mockResolvedValue({ data: { ...pending, state: 'PAID', amount_due: 0, receipt: { verified_amount: '100.00', safe_reference: 'REF-5678' } } });
  await render();
  expect(container.querySelector('form')).toBeNull();
  expect(container.textContent).toContain('Payment received and verified');
});
test('receipt requires payment pending repair stage', async () => {
  await render({ admin: true, repairStatus: 'REPAIR_COMPLETED' });
  expect(container.querySelector('form')).toBeNull();
  expect(container.textContent).toContain('Set the repair status to payment pending');
});
test('load failure is visible', async () => {
  mockGet.mockRejectedValue(new Error('unavailable'));
  await render(); expect(container.textContent).toContain('Could not load payment details');
});
