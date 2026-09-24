import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { UsersPage } from './UsersPage';
import { api } from '../../api/client';
import { ToastProvider } from '../../context/ToastContext';

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('UsersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockUsersData = {
    human_users: [
      {
        username: 'rahat',
        uid: 1000,
        gid: 1000,
        shell: '/bin/bash',
        home: '/home/rahat',
        groups: ['wheel', 'docker', 'audio'],
        is_human: true,
      },
      {
        username: 'alice',
        uid: 1001,
        gid: 1001,
        shell: '/bin/zsh',
        home: '/home/alice',
        groups: ['users'],
        is_human: true,
      },
    ],
    system_users: [],
    groups_categorized: { admin: ['wheel', 'sudo'] },
    active_sessions: [
      { user: 'rahat', tty: 'pts/0', from: '192.168.1.100', login_time: '14:20:00', idle: '12s' },
    ],
    login_history: [],
    security: {},
    metrics: {
      active_sessions_count: 1,
      human_users_count: 2,
      total_ssh_keys: 3,
      is_elevated: true,
    },
    current_user: {
      username: 'rahat',
      uid: 1000,
      gid: 1000,
      home: '/home/rahat',
      shell: '/bin/bash',
      groups: ['wheel'],
      is_admin: true,
      can_elevate: true,
      admin_remaining_seconds: 600,
    },
  };

  it('renders user accounts, metrics, and active sessions', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockUsersData);

    render(
      <ToastProvider>
        <MemoryRouter>
          <UsersPage />
        </MemoryRouter>
      </ToastProvider>
    );

    const userMatches = await screen.findAllByText('rahat');
    expect(userMatches.length).toBeGreaterThan(0);
    expect(screen.getByText('alice')).toBeInTheDocument();
    expect(screen.getByText('/home/rahat')).toBeInTheDocument();
    expect(screen.getByText('/home/alice')).toBeInTheDocument();
    expect(screen.getByText('pts/0')).toBeInTheDocument();
    expect(screen.getByText('192.168.1.100')).toBeInTheDocument();
  });

  it('terminates active session via confirmation modal', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockUsersData);
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      message: 'Session terminated',
    });

    render(
      <ToastProvider>
        <MemoryRouter>
          <UsersPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findAllByText('rahat');

    const disconnectBtn = screen.getByRole('button', { name: /Disconnect/i });
    act(() => {
      fireEvent.click(disconnectBtn);
    });

    // Confirmation modal appears
    expect(await screen.findByText(/Disconnect Session/i)).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to terminate session on pts\/0/i)).toBeInTheDocument();

    const dialog = screen.getByRole('dialog');
    const confirmBtn = within(dialog).getByRole('button', { name: /Terminate Session/i });

    act(() => {
      fireEvent.click(confirmBtn);
    });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/api/users/session/terminate', {
        tty: 'pts/0',
      });
    });
  });

  it('opens SSH keys modal and displays installed keys', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/ssh-keys')) {
        return Promise.resolve({
          username: 'rahat',
          keys: ['ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIG5... rahul@laptop'],
        });
      }
      return Promise.resolve(mockUsersData);
    });

    render(
      <ToastProvider>
        <MemoryRouter>
          <UsersPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findAllByText('rahat');

    const sshBtns = screen.getAllByRole('button', { name: /SSH Keys/i });
    act(() => {
      fireEvent.click(sshBtns[0]);
    });

    expect(await screen.findByText(/Authorized SSH Keys: rahat/i)).toBeInTheDocument();
    expect(screen.getByText(/rahul@laptop/i)).toBeInTheDocument();
  });
});
