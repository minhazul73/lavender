import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { App } from './App';
import { api } from './api/client';

vi.mock('./api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
  registerElevationHandler: vi.fn(),
  unregisterElevationHandler: vi.fn(),
}));

vi.mock('./hooks/useSSE', () => ({
  useSSE: vi.fn(() => ({
    data: {
      cpu: { count: 4, load5: 0.5, per_core_usage: [] },
      ram: { total: 4000000, used: 2000000, used_pct: 50 },
      battery: { present: true, percentage: 80, charging: false },
      network: { tx_rate: 100, rx_rate: 200 },
      thermal: [],
    },
    status: 'connected',
  })),
}));

describe('App Routing and Homepage Public Access', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, 'Test', '/');
  });

  it('allows unauthenticated visitors to view the homepage when requireAuthForHomepage is false', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/auth/me')) {
        return Promise.reject(new Error('Unauthorized'));
      }
      if (url.includes('/auth/config')) {
        return Promise.resolve({ require_auth_for_homepage: false });
      }
      if (url.includes('/device/info')) {
        return Promise.resolve({ model: 'Test Linux Device', os_name: 'Linux' });
      }
      return Promise.resolve({});
    });

    render(<App />);

    // Should render Topbar title "Live Overview" and not redirect to Login
    expect(await screen.findByText('Live Overview')).toBeInTheDocument();
    expect(screen.getByText('Sign In')).toBeInTheDocument();
  });

  it('redirects unauthenticated visitors away from protected routes like /services', async () => {
    window.history.pushState({}, 'Test', '/services');

    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/auth/me')) {
        return Promise.reject(new Error('Unauthorized'));
      }
      if (url.includes('/auth/config')) {
        return Promise.resolve({ require_auth_for_homepage: false });
      }
      return Promise.resolve({});
    });

    render(<App />);

    // Should redirect to LoginPage
    expect(await screen.findByRole('button', { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByText(/sign in with your linux system credentials/i)).toBeInTheDocument();
  });

  it('redirects unauthenticated visitors on homepage when requireAuthForHomepage is toggled true', async () => {
    window.history.pushState({}, 'Test', '/');

    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/auth/me')) {
        return Promise.reject(new Error('Unauthorized'));
      }
      if (url.includes('/auth/config')) {
        return Promise.resolve({ require_auth_for_homepage: true });
      }
      return Promise.resolve({});
    });

    render(<App />);

    // Should redirect to LoginPage
    expect(await screen.findByRole('button', { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByText(/sign in with your linux system credentials/i)).toBeInTheDocument();
  });
});
