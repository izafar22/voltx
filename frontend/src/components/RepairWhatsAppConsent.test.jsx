import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { RepairWhatsAppConsentView } from './RepairWhatsAppConsent';

jest.mock('@/lib/utils', () => ({ cn: (...values) => values.filter(Boolean).join(' ') }), { virtual: true });
let root, container;
beforeEach(() => { global.IS_REACT_ACT_ENVIRONMENT = true; container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container); });
afterEach(() => { act(() => root.unmount()); container.remove(); });
const render = props => act(() => root.render(<RepairWhatsAppConsentView onChange={() => {}} {...props} />));
test('verified consent starts unchecked and preserves the server binding when selected', () => {
  const data = { available: true, destination: '••42', identity_key: 'identity', binding: 'purpose-bound-token' };
  const onChange = jest.fn(); render({ data, onChange });
  const input = container.querySelector('input'); expect(input.checked).toBe(false); expect(input.disabled).toBe(false);
  act(() => input.click()); expect(onChange).toHaveBeenLastCalledWith(data);
  render({ data, value: data, onChange }); act(() => input.click()); expect(onChange).toHaveBeenLastCalledWith(null);
});
test('unavailable state cannot opt in and keeps account tracking visible', () => {
  const onChange = jest.fn(); render({ data: { available: false }, onChange });
  const input = container.querySelector('input'); act(() => input.click());
  expect(input.disabled).toBe(true); expect(onChange).not.toHaveBeenCalled(); expect(container.textContent).toContain('follow your repair in your account');
});
test('verification is explicit and only available for the supported linking flow', () => {
  const onVerify = jest.fn(); render({ data: { reason_code: 'verify_phone' }, canVerify: true, onVerify });
  act(() => container.querySelector('button').click()); expect(onVerify).toHaveBeenCalledTimes(1);
  render({ data: { reason_code: 'verify_phone' }, canVerify: false }); expect(container.querySelector('button')).toBeNull();
});
