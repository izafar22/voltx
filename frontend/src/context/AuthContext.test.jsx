import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { AuthProvider, useAuth } from './AuthContext';
const mockGet = jest.fn(), mockPost = jest.fn(), mockClear = jest.fn();
jest.mock('../lib/api', () => ({ api: { get: (...args) => mockGet(...args), post: (...args) => mockPost(...args) } }));
jest.mock('@tanstack/react-query', () => ({ useQueryClient: () => ({ clear: mockClear }) }));
let context, container, root;
function Consumer() { context = useAuth(); return <span>{context.user?.name || 'signed out'}</span>; }
beforeEach(() => { global.IS_REACT_ACT_ENVIRONMENT = true; jest.clearAllMocks(); container=document.createElement('div'); document.body.appendChild(container); root=createRoot(container); });
afterEach(() => { act(() => root.unmount()); container.remove(); localStorage.clear(); });
const mount = async () => act(async () => root.render(<AuthProvider><Consumer /></AuthProvider>));
test('restores cookie session without local token and cleans up old JWT', async () => {
  localStorage.setItem('ev_token','old'); mockGet.mockResolvedValue({ data:{name:'Asha'} }); await mount();
  expect(mockGet).toHaveBeenCalledWith('/auth/me'); expect(localStorage.getItem('ev_token')).toBeNull(); expect(context.user.name).toBe('Asha');
});
test('login and logout clear cached customer data; logout calls backend', async () => {
  mockGet.mockRejectedValue({ response:{status:401} }); await mount(); act(() => context.login({name:'New customer'}));
  mockPost.mockResolvedValue({data:{ok:true}}); await act(async () => context.logout());
  expect(mockPost).toHaveBeenCalledWith('/auth/logout'); expect(context.user).toBeNull(); expect(mockClear).toHaveBeenCalledTimes(2);
});
test('failed logout does not pretend the server session ended', async () => {
  mockGet.mockResolvedValue({data:{name:'Asha'}}); await mount(); mockPost.mockRejectedValue(new Error('offline'));
  await act(async () => context.logout()); expect(context.user.name).toBe('Asha'); expect(context.authError).toContain('Unable to sign out');
});
