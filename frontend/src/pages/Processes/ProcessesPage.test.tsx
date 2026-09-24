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
      { pid: 1234, user: 'root', cpu: 15.2, mem: 4.5, command: '/usr/bin/dockerd', name: 'dockerd' },
      { pid: 5678, user: 'rahat', cpu: 2.1, mem: 8.9, command: 'python3 server/main.py', name: 'python3' },
      { pid: 9012, user: 'systemd', cpu: 0.1, mem: 0.8, command: '/lib/systemd/systemd-resolved', name: 'systemd-resolved' },
    ],
    load: { '1m': 0.85, '5m': 1.12, '15m': 0.95 },
    memory: { total: 8192, used: 4096 },
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
});
