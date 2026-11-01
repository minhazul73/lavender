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
  const { session, loading, isElevated, requireAuthForHomepage, login, logout, elevate, dropElevation } = useAuth();

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <div data-testid="user">{session ? session.username : 'Anonymous'}</div>
      <div data-testid="elevated">{isElevated ? 'Elevated' : 'Not Elevated'}</div>
      <div data-testid="auth-home">{String(requireAuthForHomepage)}</div>
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
    let meCallCount = 0;
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/auth/config')) {
        return Promise.resolve({ require_auth_for_homepage: false });
      }
      meCallCount++;
      if (meCallCount === 1) {
        return Promise.reject(new Error('Unauthorized'));
      }
      return Promise.resolve({
        username: 'bob',
        uid: 1001,
        gid: 1001,
        home: '/home/bob',
        shell: '/bin/bash',
        groups: ['users'],
        is_admin: false,
        has_sudo_ticket: false,
      });
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

  it('provides requireAuthForHomepage defaulting to false', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/auth/config')) {
        return Promise.resolve({ require_auth_for_homepage: false });
      }
      return Promise.reject(new Error('Unauthorized'));
    });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    const authHomeEl = await screen.findByTestId('auth-home');
    expect(authHomeEl.textContent).toBe('false');
  });

  it('updates requireAuthForHomepage when server indicates homepage is locked', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/auth/config')) {
        return Promise.resolve({ require_auth_for_homepage: true });
      }
      return Promise.reject(new Error('Unauthorized'));
    });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    const authHomeEl = await screen.findByTestId('auth-home');
    expect(authHomeEl.textContent).toBe('true');
  });

  it('does not redirect to /login when logging out from homepage with public homepage', async () => {
    window.history.pushState({}, 'Test', '/');

    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/auth/config')) {
        return Promise.resolve({ require_auth_for_homepage: false });
      }
      return Promise.resolve({
        username: 'alice',
        uid: 1000,
        gid: 1000,
        home: '/home/alice',
        shell: '/bin/bash',
        groups: ['wheel'],
        is_admin: false,
      });
    });
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ success: true });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(await screen.findByText('alice')).toBeInTheDocument();

    await act(async () => {
      screen.getByText('Logout').click();
    });

    expect(api.post).toHaveBeenCalledWith('/auth/logout');
    expect(await screen.findByText('Anonymous')).toBeInTheDocument();
    expect(window.location.pathname).toBe('/');
  });
});
