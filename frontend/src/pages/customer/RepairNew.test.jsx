import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import RepairNew from './RepairNew';
const mockInvalidate = jest.fn();
const mockNavigate = jest.fn(), mockPost = jest.fn(), mockPatch = jest.fn(), mockError = jest.fn();
let mockChargers = [], mockRole = 'customer';
jest.mock('react-router-dom', () => ({ useNavigate: () => mockNavigate }), { virtual: true });
jest.mock('@tanstack/react-query', () => ({ useQuery: () => ({ data: mockChargers }), useQueryClient: () => ({ invalidateQueries: mockInvalidate }) }));
jest.mock('../../lib/api', () => ({ api: { post: (...args) => mockPost(...args), patch: (...args) => mockPatch(...args) } }));
jest.mock('../../context/AuthContext', () => ({ useAuth: () => ({ user: { role: mockRole } }) }));
jest.mock('../../components/layout/CustomerShell', () => ({ CustomerShell: ({ children }) => <main>{children}</main> }));
jest.mock('sonner', () => ({ toast: { error: (...args) => mockError(...args), message: jest.fn() } }));
jest.mock('framer-motion', () => ({ motion: { div: ({ children, initial, animate, ...props }) => <div {...props}>{children}</div> } }));
jest.mock('../../components/ui/button', () => ({ Button: ({ children, variant, ...props }) => <button {...props}>{children}</button> }));
jest.mock('../../components/ui/input', () => ({ Input: props => <input {...props} /> }));
jest.mock('../../components/ui/textarea', () => ({ Textarea: props => <textarea {...props} /> }));
jest.mock('../../components/ui/label', () => ({ Label: props => <label {...props} /> }));
jest.mock('../../components/ui/select', () => {
  const React = require('react');
  const Context = React.createContext({});
  return {
    Select: ({ value, onValueChange, children }) => <Context.Provider value={{ value, onValueChange }}>{children}</Context.Provider>,
    SelectTrigger: ({ children, ...props }) => { const ctx = React.useContext(Context); return <select {...props} value={ctx.value} onChange={e => ctx.onValueChange(e.target.value)}><option value="">Choose</option>{['AC', 'DC', 'PORTABLE', 'OTHER', 'NOT_SURE', 'Not charging', 'VOLTX1'].map(v => <option key={v} value={v}>{v}</option>)}</select>; },
    SelectValue: () => null, SelectContent: () => null, SelectItem: () => null,
  };
});
let root, container;
const el = id => container.querySelector(`[data-testid="${id}"]`);
const click = id => act(() => el(id).click());
const change = (id, value) => act(() => {
  const node = el(id);
  const proto = node.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : node.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, 'value').set.call(node, value);
  node.dispatchEvent(new Event(node.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }));
});
const submit = () => container.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
const fill = () => { change('brand-input', ' ABB '); change('model-input', 'Terra AC'); change('type-select', 'NOT_SURE'); change('description-input', 'Stops after a few seconds.'); };
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true; jest.clearAllMocks(); mockRole = 'customer'; mockChargers = [];
  mockPost.mockResolvedValue({ data: { id: 'r1', repair_request_number: 'REP-001' } }); mockPatch.mockResolvedValue({});
  container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); container.remove(); });
const render = () => act(() => root.render(<RepairNew />));
test('readable single-page sections, labels and mobile stacking', () => {
  render(); expect([...container.querySelectorAll('h2')].map(n => n.textContent)).toEqual(['1. Choose your charger', '2. Charger details', '3. Tell us what’s wrong', '4. Add photos (optional)', '5. Review and submit']);
  expect(el('repair-new-page').className).toContain('max-w-4xl');
  expect(el('source-mine').parentElement.className).toContain('grid-cols-1');
  expect(container.querySelector('label[for="brand"]')).not.toBeNull();
  expect(el('photo-input').className).not.toContain('hidden');
  expect(container.textContent).toContain('Don’t know the type?');
});
test('inline errors associate with controls, focus first field and clear on correction', () => {
  render(); act(() => submit()); expect(mockPost).not.toHaveBeenCalled(); expect(document.activeElement).toBe(el('brand-input'));
  expect(container.querySelectorAll('[role="alert"]')).toHaveLength(4);
  expect(el('brand-input').getAttribute('aria-invalid')).toBe('true');
  expect(el('brand-input').getAttribute('aria-describedby')).toBe('brand-error');
  change('brand-input', ' '); expect(container.querySelector('#brand-error')).not.toBeNull();
  fill(); expect(container.querySelectorAll('[role="alert"]')).toHaveLength(0);
});
test('source selection communicates state and empty registered source offers recovery', () => {
  render(); click('source-mine'); expect(el('source-mine').getAttribute('aria-pressed')).toBe('true'); expect(el('brand-input')).toBeNull();
  act(() => submit()); expect(document.activeElement.id).toBe('chargerId');
  act(() => container.querySelector('#chargerId').click()); expect(el('brand-input')).not.toBeNull();
});
test('registered charger selection preserves payload and details', async () => {
  mockRole = 'owner'; mockChargers = [{ charger_id: 'VOLTX1', name: 'Home charger', connector: 'Type 2', max_power_kw: 7.4 }]; render(); click('source-mine');
  change('my-charger-select', 'VOLTX1'); change('description-input', 'Not working');
  expect(el('selected-charger-info').textContent).toContain('Home charger');
  await act(async () => submit()); expect(mockPost).toHaveBeenCalledWith('/repairs', { customer_type: 'STATION_OWNER', charger_id: 'VOLTX1', problem_description: 'Not working', reported_category: null, photos: [] });
});
test('review separates description and successful submission preserves contract and navigation', async () => {
  render(); fill(); change('category-select', 'Not charging');
  expect([...el('review-section').querySelectorAll('dt')].map(n => n.textContent)).toEqual(['Charger', 'Problem', 'Description', 'Photos']);
  expect(el('review-section').textContent).toContain('Terra AC');
  await act(async () => submit());
  expect(mockPost).toHaveBeenCalledWith('/repairs', { customer_type: 'RETAIL', problem_description: 'Stops after a few seconds.', reported_category: 'Not charging', photos: [], charger_info: { brand: 'ABB', model: 'Terra AC', charger_type: null, serial_number: null, power_rating: null, purchase_date: null } });
  expect(mockPatch).toHaveBeenCalledWith('/repairs/r1/status', { status: 'AWAITING_SHIPMENT' });
  expect(mockInvalidate).toHaveBeenCalledWith({ queryKey: ['repairs-mine'] });
  expect(el('repair-confirmation')).not.toBeNull(); expect(el('repair-number').textContent).toContain('REP-001'); expect(container.querySelectorAll('ol li')).toHaveLength(5);
  click('view-repair-btn'); expect(mockNavigate).toHaveBeenLastCalledWith('/repairs/r1'); click('back-dashboard-btn'); expect(mockNavigate).toHaveBeenLastCalledWith('/app');
});
test('duplicate submissions are blocked and failures allow retry', async () => {
  let reject; mockPost.mockImplementationOnce(() => new Promise((resolve, fail) => { reject = fail; })); render(); fill();
  act(() => { submit(); submit(); }); expect(mockPost).toHaveBeenCalledTimes(1); expect(el('submit-repair-btn').disabled).toBe(true); expect(el('submit-repair-btn').textContent).toContain('Submitting');
  await act(async () => reject(new Error('offline'))); expect(el('submit-repair-btn').disabled).toBe(false); expect(mockError).toHaveBeenCalled();
  await act(async () => submit()); expect(el('repair-confirmation')).not.toBeNull();
});
test('photos retain data URLs, can be removed and reject unsupported/oversized files', async () => {
  render();
  const files = [new File(['photo'], 'charger.png', { type: 'image/png' }), new File(['text'], 'notes.txt', { type: 'text/plain' }), new File(['x'], 'large.jpg', { type: 'image/jpeg' })];
  Object.defineProperty(files[2], 'size', { value: 6 * 1024 * 1024 });
  await act(async () => { Object.defineProperty(el('photo-input'), 'files', { value: files, configurable: true }); el('photo-input').dispatchEvent(new Event('change', { bubbles: true })); await new Promise(resolve => setTimeout(resolve, 30)); });
  expect(mockError).toHaveBeenCalledTimes(2); expect(el('photo-0').querySelector('img').src).toMatch(/^data:image\/png;base64,/);
  expect(el('remove-photo-0').getAttribute('aria-label')).toContain('charger.png'); expect(el('review-section').textContent).toContain('1 attached');
  click('remove-photo-0'); expect(el('photo-0')).toBeNull(); expect(el('review-section').textContent).toContain('0 attached');
});
