import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ProcessesPage } from './ProcessesPage';
import { api } from '../../api/client';
import { ToastProvider } from '../../context/ToastContext';

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('ProcessesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockProcessesData = {
    processes: [
      { pid: 1234, user: 'root', cpu: 15.2, mem: 120000, mem_pct: 12.5, command: '/usr/bin/dockerd', name: 'dockerd', stat: 'Sl', time: '1:45' },
      { pid: 5678, user: 'rahat', cpu: 2.1, mem: 46080, mem_pct: 4.8, command: 'python3 server/main.py', name: 'python3', stat: 'R', time: '0:24' },
      { pid: 9012, user: 'systemd', cpu: 0.1, mem: 8192, mem_pct: 0.8, command: '/lib/systemd/systemd-resolved', name: 'systemd-resolved', stat: 'S', time: '0:02' },
    ],
    load: {
      '1min': 0.85,
      '5min': 1.12,
      '15min': 0.95,
      '1m': 0.85,
      '5m': 1.12,
      '15m': 0.95,
      running: '2',
      total: '240',
      uptime_formatted: '2d 4h 12m',
    },
    memory: {
      parsed: {
        total: '8.0G',
        used: '4.0G',
        free: '3.2G',
        percent: 50.0,
        swap_total: '2.0G',
        swap_used: '0B',
      },
    },
  };

  it('renders process list, load average, and task metrics', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockProcessesData);

    render(
      <ToastProvider>
        <MemoryRouter>
          <ProcessesPage />
        </MemoryRouter>
      </ToastProvider>
    );

    expect(await screen.findByText('dockerd')).toBeInTheDocument();
    expect(screen.getByText('python3')).toBeInTheDocument();
    expect(screen.getByText('systemd-resolved')).toBeInTheDocument();
    expect(screen.getByText('1234')).toBeInTheDocument();
    expect(screen.getByText('0.85')).toBeInTheDocument();
  });

  it('filters processes by name or command', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockProcessesData);

    render(
      <ToastProvider>
        <MemoryRouter>
          <ProcessesPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findByText('dockerd');

    const searchInput = screen.getByPlaceholderText(/search by pid/i);
    fireEvent.change(searchInput, { target: { value: 'python' } });

    expect(screen.getByText('python3')).toBeInTheDocument();
    expect(screen.queryByText('dockerd')).toBeNull();
  });

  it('prompts kill confirmation modal and sends kill request', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockProcessesData);
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      action: 'kill',
      pid: 1234,
      success: true,
    });

    render(
      <ToastProvider>
        <MemoryRouter>
          <ProcessesPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findByText('dockerd');

    const killBtns = screen.getAllByRole('button', { name: /kill/i });
    act(() => {
      fireEvent.click(killBtns[0]);
    });

    // Modal appears
    expect(await screen.findByText(/Terminate Process/i)).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to send SIGKILL to 'dockerd' \(PID: 1234\)\?/i)).toBeInTheDocument();

    const dialog = screen.getByRole('dialog');
    const confirmBtn = within(dialog).getByRole('button', { name: /Terminate \(SIGKILL\)/i });

    act(() => {
      fireEvent.click(confirmBtn);
    });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/api/system/processes/kill?pid=1234');
    });
  });

  it('renders telemetry cards including memory usage and system uptime', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockProcessesData);

    render(
      <ToastProvider>
        <MemoryRouter>
          <ProcessesPage />
        </MemoryRouter>
      </ToastProvider>
    );

    expect(await screen.findByText('Memory Usage')).toBeInTheDocument();
    expect(screen.getByText('4.0G of 8.0G utilized')).toBeInTheDocument();
    expect(screen.getByText('50.0%')).toBeInTheDocument();
    expect(screen.getByText('System Uptime')).toBeInTheDocument();
    expect(screen.getByText('2d 4h 12m')).toBeInTheDocument();
    expect(screen.getByText(/total system processes/i)).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('filters processes by user dropdown', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockProcessesData);

    render(
      <ToastProvider>
        <MemoryRouter>
          <ProcessesPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findByText('dockerd');
    expect(screen.getByText('python3')).toBeInTheDocument();

    const userSelect = screen.getByLabelText(/user:/i);
    fireEvent.change(userSelect, { target: { value: 'rahat' } });

    expect(screen.getByText('python3')).toBeInTheDocument();
    expect(screen.queryByText('dockerd')).toBeNull();
  });

  it('correctly formats memory size and percentage without data corruption', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockProcessesData);

    render(
      <ToastProvider>
        <MemoryRouter>
          <ProcessesPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findByText('dockerd');
    // 120000 KB is 117.2 MB, pct is (12.5%)
    expect(screen.getByText('117.2 MB')).toBeInTheDocument();
    expect(screen.getByText('(12.5%)')).toBeInTheDocument();
    // Ensure raw KB value is NEVER formatted as percentage
    expect(screen.queryByText(/120000\.0%/)).toBeNull();
  });
});
