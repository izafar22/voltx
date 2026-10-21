import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import RepairPaymentVerification from './RepairPaymentVerification';
const mockPatch = jest.fn();
jest.mock('../lib/api', () => ({ api: { patch: (...args) => mockPatch(...args) } }));
jest.mock('./ui/button', () => ({ Button: ({ children, ...props }) => <button {...props}>{children}</button> }));
jest.mock('./ui/input', () => ({ Input: props => <input {...props} /> }));
jest.mock('./ui/label', () => ({ Label: props => <label {...props} /> }));
let root, container, saved;
const change = (id, value) => act(() => {
  const node = container.querySelector(`#${id}`);
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(node, value);
  node.dispatchEvent(new Event('input', { bubbles: true }));
});
const submit = () => container.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  mockPatch.mockReset(); saved = jest.fn();
  container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container);
  act(() => root.render(<RepairPaymentVerification repair={{ id: 'repair-test' }} onSaved={saved} />));
});
afterEach(() => { act(() => root.unmount()); container.remove(); });
test('requires an explicit verified balance and reference', async () => {
  await act(async () => submit()); expect(mockPatch).not.toHaveBeenCalled();
  change('verified-due', '-1'); change('payment-reference', 'test reconciliation');
  await act(async () => submit()); expect(mockPatch).not.toHaveBeenCalled();
});
test('saves verified amount without status change or payment collection', async () => {
  mockPatch.mockResolvedValue({ data: { ok: true } });
  change('verified-due', '1750'); change('payment-reference', ' test reconciliation ');
  await act(async () => submit());
  expect(mockPatch).toHaveBeenCalledTimes(1);
  expect(mockPatch).toHaveBeenCalledWith('/repairs/repair-test/payment', { amount_due: 1750, reference: 'test reconciliation' });
  expect(saved).toHaveBeenCalledTimes(1);
  expect(container.textContent).toContain('does not collect money');
});
test('validation failures remain readable and allow correction', async () => {
  mockPatch.mockRejectedValue({ response: { data: { detail: [{ msg: 'invalid' }] } } });
  change('verified-due', '10'); change('payment-reference', 'test reference');
  await act(async () => submit());
  expect(container.querySelector('[role="status"]').textContent).toContain('Could not save');
  expect(container.querySelector('button').disabled).toBe(false);
});
