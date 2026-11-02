import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { PowerPage } from './PowerPage';
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
    session: {
      username: 'rahat',
      uid: 1000,
      gid: 1000,
      home: '/home/rahat',
      shell: '/bin/bash',
      groups: ['wheel'],
      is_admin: true,
      can_elevate: true,
      is_elevated: true,
    },
    openElevate: vi.fn(),
    logout: vi.fn(),
  }),
}));

describe('PowerPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockPowerState = {
    active_governor: 'schedutil',
    available_governors: ['powersave', 'schedutil', 'performance'],
    scheduled: {
      scheduled: false,
      details: null,
    },
  };

  it('renders system operations, active CPU governor, and scheduling presets', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockPowerState);

    render(
      <ToastProvider>
        <MemoryRouter>
          <PowerPage />
        </MemoryRouter>
      </ToastProvider>
    );

    expect(await screen.findByText(/Power & Lifecycle Management/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /^System Reboot$/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /^Power Off$/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /^Suspend to RAM$/i })).toBeInTheDocument();
    expect(screen.getByText(/Active: schedutil/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /^Power Saver/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /^High Performance/i })).toBeInTheDocument();
  });

  it('changes CPU frequency governor on user action', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockPowerState);
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ success: true });

    render(
      <ToastProvider>
        <MemoryRouter>
          <PowerPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findByText(/Active: schedutil/i);

    const powersaveBtn = screen.getByRole('button', { name: /Activate Power Saver/i });
    act(() => {
      fireEvent.click(powersaveBtn);
    });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/api/power/governor?governor=powersave');
    });
  });

  it('schedules a timed power action via presets and custom form', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockPowerState);
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ success: true });

    render(
      <ToastProvider>
        <MemoryRouter>
          <PowerPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findByText(/Power & Lifecycle Management/i);

    // Preset schedule button: Reboot in 15m
    const presetBtn = screen.getByRole('button', { name: /Reboot in 15m/i });
    act(() => {
      fireEvent.click(presetBtn);
    });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/api/power/schedule',
        expect.objectContaining({
          action: 'reboot',
          minutes: 15,
        })
      );
    });

    // Custom schedule form: Power Off in 30 minutes
    const actionSelect = screen.getByRole('combobox');
    const minutesInput = screen.getByRole('spinbutton');
    const scheduleBtn = screen.getByRole('button', { name: /^Schedule$/i });

    act(() => {
      fireEvent.change(actionSelect, { target: { value: 'poweroff' } });
      fireEvent.change(minutesInput, { target: { value: '30' } });
      fireEvent.click(scheduleBtn);
    });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/api/power/schedule',
        expect.objectContaining({
          action: 'poweroff',
          minutes: 30,
        })
      );
    });
  });

  it('displays pending schedule banner and allows cancellation', async () => {
    const pendingPowerState = {
      ...mockPowerState,
      scheduled: {
        scheduled: true,
        action: 'reboot',
        minutes: 15,
        details: 'Reboot scheduled in 15 minutes',
      },
    };
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(pendingPowerState);
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ success: true });

    render(
      <ToastProvider>
        <MemoryRouter>
          <PowerPage />
        </MemoryRouter>
      </ToastProvider>
    );

    expect(await screen.findByText(/Reboot scheduled in 15 minutes/i)).toBeInTheDocument();

    const cancelBtn = screen.getByRole('button', { name: /Cancel Scheduled Action/i });
    act(() => {
      fireEvent.click(cancelBtn);
    });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/api/power/cancel-scheduled');
    });
  });

  it('confirms immediate reboot and switches to poller view', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockPowerState);
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ success: true });

    render(
      <ToastProvider>
        <MemoryRouter>
          <PowerPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findByText(/Power & Lifecycle Management/i);

    const rebootBtn = screen.getByRole('button', { name: /^Reboot System$/i });
    act(() => {
      fireEvent.click(rebootBtn);
    });

    expect(await screen.findByText(/Confirm System Reboot/i)).toBeInTheDocument();

    const dialog = screen.getByRole('dialog');
    const confirmBtn = within(dialog).getByRole('button', { name: /Proceed with Reboot/i });

    act(() => {
      fireEvent.click(confirmBtn);
    });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/api/power/reboot');
    });

    expect(await screen.findByText(/Rebooting System.../i)).toBeInTheDocument();
  });

  it('confirms immediate power off', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockPowerState);
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ success: true });

    render(
      <ToastProvider>
        <MemoryRouter>
          <PowerPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findByText(/Power & Lifecycle Management/i);

    const poweroffBtn = screen.getByRole('button', { name: /^Power Off Device$/i });
    act(() => {
      fireEvent.click(poweroffBtn);
    });

    expect(await screen.findByText(/Confirm Power Off/i)).toBeInTheDocument();

    const dialog = screen.getByRole('dialog');
    const confirmBtn = within(dialog).getByRole('button', { name: /Power Off Completely/i });

    act(() => {
      fireEvent.click(confirmBtn);
    });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/api/power/poweroff');
    });
  });
});
