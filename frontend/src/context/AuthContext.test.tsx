import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { AuthProvider, useAuth } from './AuthContext';
import { api } from '../api/client';

vi.mock('../api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
  registerElevationHandler: vi.fn(),
  unregisterElevationHandler: vi.fn(),
}));

const TestComponent = () => {
  const { session, loading, isElevated, login, logout, elevate, dropElevation } = useAuth();

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <div data-testid="user">{session ? session.username : 'Anonymous'}</div>
      <div data-testid="elevated">{isElevated ? 'Elevated' : 'Not Elevated'}</div>
      <button onClick={() => login('admin', 'password')}>Login</button>
      <button onClick={() => logout()}>Logout</button>
      <button onClick={() => elevate('secret')}>Elevate</button>
      <button onClick={() => dropElevation()}>Drop</button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches profile on mount and sets session', async () => {
    const mockProfile = {
      username: 'alice',
      uid: 1000,
      gid: 1000,
      home: '/home/alice',
      shell: '/bin/bash',
      groups: ['wheel'],
      is_admin: true,
      has_sudo_ticket: true,
    };
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockProfile);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByText('Loading...')).toBeInTheDocument();

    const userEl = await screen.findByTestId('user');
    expect(userEl.textContent).toBe('alice');
    expect(screen.getByTestId('elevated').textContent).toBe('Elevated');
  });

  it('handles unauthenticated state on 401', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Unauthorized'));

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    const userEl = await screen.findByTestId('user');
    expect(userEl.textContent).toBe('Anonymous');
    expect(screen.getByTestId('elevated').textContent).toBe('Not Elevated');
  });

  it('calls login endpoint and refreshes profile', async () => {
    (api.get as ReturnType<typeof vi.fn>)
      .mockRejectedValueOnce(new Error('Unauthorized'))
      .mockResolvedValueOnce({
        username: 'bob',
        uid: 1001,
        gid: 1001,
        home: '/home/bob',
        shell: '/bin/bash',
        groups: ['users'],
        is_admin: false,
        has_sudo_ticket: false,
      });

    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      next: '/',
      username: 'bob',
    });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await screen.findByText('Anonymous');

    await act(async () => {
      screen.getByText('Login').click();
    });

    expect(api.post).toHaveBeenCalledWith('/auth/login', {
      username: 'admin',
      password: 'password',
      next: '/',
    });
    expect(await screen.findByText('bob')).toBeInTheDocument();
  });
});
