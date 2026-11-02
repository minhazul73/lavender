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

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({
    session: { username: 'rahat', is_admin: true },
    isElevated: true,
    openElevationModal: vi.fn().mockResolvedValue(true),
    dropElevation: vi.fn(),
  }),
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
        home_storage: {
          total_gb: 50.0,
          used_gb: 15.0,
          free_gb: 35.0,
          percent_used: 30.0,
        },
        ssh_keys_count: 1,
      },
      {
        username: 'alice',
        uid: 1001,
        gid: 1001,
        shell: '/bin/zsh',
        home: '/home/alice',
        groups: ['users'],
        is_human: true,
        ssh_keys_count: 0,
      },
    ],
    system_users: [
      {
        username: 'daemon',
        uid: 1,
        gid: 1,
        shell: '/usr/sbin/nologin',
        home: '/usr/sbin',
        groups: ['daemon'],
      },
    ],
    groups_categorized: [
      {
        name: 'wheel',
        gid: 10,
        members: ['rahat'],
        category: 'Privileged',
        description: 'Administrative elevation privileges',
        member_count: 1,
      },
      {
        name: 'audio',
        gid: 29,
        members: ['rahat'],
        category: 'Hardware',
        description: 'Audio playback and recording',
        member_count: 1,
      },
    ],
    active_sessions: [
      { user: 'rahat', tty: 'pts/0', from: '192.168.1.100', login_time: '14:20:00', idle: '12s' },
    ],
    login_history: [
      { user: 'rahat', tty: 'pts/0', host: '192.168.1.100', time: 'Mon 14:20' },
    ],
    security: {
      elevation_engine: 'sudo',
      visudo_ok: true,
      sshd_active: true,
      root_ssh_login: 'prohibit-password',
      password_auth: 'yes',
    },
    metrics: {
      active_sessions_count: 1,
      human_users_count: 2,
      total_ssh_keys: 1,
      is_elevated: true,
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
    expect(screen.getByText(/pts\/0/i)).toBeInTheDocument();
    expect(screen.getByText(/192\.168\.1\.100/i)).toBeInTheDocument();
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

    // Switch to active sessions tab
    const sessionsTab = screen.getByRole('button', { name: /Active Sessions/i });
    act(() => {
      fireEvent.click(sessionsTab);
    });

    const disconnectBtn = await screen.findByRole('button', { name: /Disconnect/i });
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

    const sshBtn = screen.getByRole('button', { name: /SSH Keys \(1\)/i });
    act(() => {
      fireEvent.click(sshBtn);
    });

    expect(await screen.findByText(/Authorized SSH Keys: rahat/i)).toBeInTheDocument();
    expect(screen.getByText(/rahul@laptop/i)).toBeInTheDocument();
  });

  it('switches tabs to Groups & Hardware and filters by category', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockUsersData);

    render(
      <ToastProvider>
        <MemoryRouter>
          <UsersPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findAllByText('rahat');

    const groupsTab = screen.getByRole('button', { name: /Groups & Hardware/i });
    act(() => {
      fireEvent.click(groupsTab);
    });

    expect(await screen.findByText('Administrative elevation privileges')).toBeInTheDocument();
    expect(screen.getByText('Audio playback and recording')).toBeInTheDocument();

    // Filter by Privileged pill
    const privPill = screen.getByRole('button', { name: /Privileged/i });
    act(() => {
      fireEvent.click(privPill);
    });

    expect(screen.getByText('wheel')).toBeInTheDocument();
    expect(screen.queryByText('audio')).not.toBeInTheDocument();
  });

  it('renders Groups & Hardware tab with responsive toolbar, cards, search, and action controls', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockUsersData);

    render(
      <ToastProvider>
        <MemoryRouter>
          <UsersPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findAllByText('rahat');

    const groupsTab = screen.getByRole('button', { name: /Groups & Hardware/i });
    act(() => {
      fireEvent.click(groupsTab);
    });

    // Check responsive containers and cards
    expect(document.querySelector('.groups-tab-container')).toBeInTheDocument();
    expect(document.querySelector('.groups-toolbar')).toBeInTheDocument();
    expect(document.querySelector('.groups-search-wrap')).toBeInTheDocument();
    expect(document.querySelector('.groups-card')).toBeInTheDocument();
    expect(document.querySelector('.groups-table')).toBeInTheDocument();
    expect(document.querySelectorAll('.group-item-row').length).toBeGreaterThan(0);
    expect(document.querySelector('.group-gid-badge')).toBeInTheDocument();

    // Test search filter
    const searchInput = screen.getByPlaceholderText(/Search groups/i);
    act(() => {
      fireEvent.change(searchInput, { target: { value: 'audio' } });
    });

    expect(screen.getByText('audio')).toBeInTheDocument();
    expect(screen.queryByText('wheel')).not.toBeInTheDocument();

    // Test Edit action opens edit modal for primary user
    const editBtn = screen.getAllByRole('button', { name: /^Edit$/i })[0];
    act(() => {
      fireEvent.click(editBtn);
    });

    expect(await screen.findByText(/Edit Groups: rahat/i)).toBeInTheDocument();
  });

  it('switches to Security & SSH Keys tab and displays posture cards', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockUsersData);

    render(
      <ToastProvider>
        <MemoryRouter>
          <UsersPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findAllByText('rahat');

    const securityTab = screen.getByRole('button', { name: /Security & SSH Keys/i });
    act(() => {
      fireEvent.click(securityTab);
    });

    expect(await screen.findByText(/Privilege Elevation Engine/i)).toBeInTheDocument();
    expect(screen.getByText(/SSH Daemon Posture/i)).toBeInTheDocument();
    expect(screen.getByText(/SSH Authorized Keys Hub/i)).toBeInTheDocument();
    expect(screen.getByText(/Syntax OK/i)).toBeInTheDocument();
  });

  it('renders active sessions and login history in Active Sessions tab with responsive classes', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockUsersData);

    render(
      <ToastProvider>
        <MemoryRouter>
          <UsersPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findAllByText('rahat');

    // Switch to active sessions tab
    const sessionsTab = screen.getByRole('button', { name: /Active Sessions/i });
    act(() => {
      fireEvent.click(sessionsTab);
    });

    expect(screen.getByText('Active Terminal & Remote Logins')).toBeInTheDocument();
    expect(screen.getByText('Recent Login History')).toBeInTheDocument();
    expect(screen.getByText('1 Online')).toBeInTheDocument();
    expect(screen.getAllByText('pts/0').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('Mon 14:20')).toBeInTheDocument();

    const activeTable = document.querySelector('.active-sessions-table');
    expect(activeTable).toBeInTheDocument();
    expect(document.querySelector('.session-item-row')).toBeInTheDocument();
    expect(document.querySelector('.history-item-row')).toBeInTheDocument();
  });

  describe('UsersPage Characterization', () => {
    it('switches between accounts, sessions, and groups tabs', async () => {
      (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockUsersData);

      render(
        <ToastProvider>
          <MemoryRouter>
            <UsersPage />
          </MemoryRouter>
        </ToastProvider>
      );

      // Accounts tab active initially
      expect((await screen.findAllByText('rahat')).length).toBeGreaterThan(0);
      expect(screen.getByText('/home/rahat')).toBeInTheDocument();

      // Switch to Groups tab
      const groupsTab = screen.getByRole('button', { name: /Groups & Hardware/i });
      act(() => {
        fireEvent.click(groupsTab);
      });
      expect(await screen.findByText('Administrative elevation privileges')).toBeInTheDocument();
      expect(screen.getByText('wheel')).toBeInTheDocument();

      // Switch to Active Sessions tab
      const sessionsTab = screen.getByRole('button', { name: /Active Sessions/i });
      act(() => {
        fireEvent.click(sessionsTab);
      });
      expect(await screen.findByText('Active Terminal & Remote Logins')).toBeInTheDocument();
      expect(screen.getAllByText('pts/0').length).toBeGreaterThanOrEqual(1);

      // Switch back to Accounts tab
      const accountsTab = screen.getByRole('button', { name: /Accounts & Users/i });
      act(() => {
        fireEvent.click(accountsTab);
      });
      expect(await screen.findByText('/home/rahat')).toBeInTheDocument();
    });

    it('opens SSH Keys modal when Manage Keys is clicked', async () => {
      (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
        if (url.includes('/ssh-keys')) {
          return Promise.resolve({
            username: 'rahat',
            keys: ['ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIG5... user@laptop'],
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

      const sshBtn = screen.getByRole('button', { name: /SSH Keys \(1\)/i });
      act(() => {
        fireEvent.click(sshBtn);
      });

      expect(await screen.findByText(/Authorized SSH Keys: rahat/i)).toBeInTheDocument();
      expect(screen.getByText(/user@laptop/i)).toBeInTheDocument();
    });

    it('opens Password Change modal when Change Password button is clicked', async () => {
      (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockUsersData);

      render(
        <ToastProvider>
          <MemoryRouter>
            <UsersPage />
          </MemoryRouter>
        </ToastProvider>
      );

      await screen.findAllByText('rahat');

      const pwdBtn = screen.getAllByRole('button', { name: /Password/i })[0];
      act(() => {
        fireEvent.click(pwdBtn);
      });

      expect(await screen.findByText(/Change Password: rahat/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Enter new password/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Repeat new password/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Update Password/i })).toBeInTheDocument();
    });
  });
});
