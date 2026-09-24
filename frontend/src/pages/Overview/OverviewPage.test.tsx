import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { OverviewPage } from './OverviewPage';
import { api } from '../../api/client';
import { useSSE } from '../../hooks/useSSE';

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
  },
}));

vi.mock('../../hooks/useSSE', () => ({
  useSSE: vi.fn(),
}));

describe('OverviewPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all telemetry cards and health pills with live data', async () => {
    (useSSE as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        cpu: {
          count: 8,
          load5: 1.45,
          per_core_usage: [
            { core: 0, usage: 25.5 },
            { core: 1, usage: 40.0 },
          ],
          cpus: [{ core: 0, frequency_mhz: 1800 }],
        },
        ram: {
          total: 8192000,
          used: 4096000,
          available: 4096000,
          used_pct: 50.0,
        },
        battery: {
          present: true,
          percentage: 85,
          charging: false,
          voltage: 4120,
          energy_rate: 3.5,
          health: 'Good',
        },
        network: {
          interface: 'wlan0',
          rx_rate: 1024 * 500, // 500 KB/s
          tx_rate: 1024 * 120, // 120 KB/s
        },
        thermal: [{ name: 'cpu-thermal', temp: 42.5 }],
      },
      status: 'connected',
    });

    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/storage')) {
        return Promise.resolve({
          disks: [
            {
              mount_point: '/',
              filesystem: '/dev/root',
              size: '58G',
              used: '12G',
              available: '43G',
              use_percent: '22%',
            },
          ],
        });
      }
      if (url.includes('/services')) {
        return Promise.resolve({
          services: [
            { unit: 'sshd.service', active: 'active' },
            { unit: 'nginx.service', active: 'failed' },
          ],
          count: 2,
        });
      }
      if (url.includes('/processes')) {
        return Promise.resolve({
          processes: [
            { pid: 100, name: 'python3', cpu: 12.5, mem: 4.2 },
          ],
        });
      }
      if (url.includes('/logs')) {
        return Promise.resolve({ logs: ['systemd: Started Lavender Dashboard'] });
      }
      return Promise.resolve({});
    });

    render(
      <MemoryRouter>
        <OverviewPage />
      </MemoryRouter>
    );

    // Verify Health status
    expect(screen.getByText(/Battery: 85%/i)).toBeInTheDocument();
    expect(screen.getByText(/Thermal: 43°C/i)).toBeInTheDocument();
    expect(screen.getByText(/RAM: 50%/i)).toBeInTheDocument();

    // Verify CPU card
    expect(screen.getByText('1.45')).toBeInTheDocument();
    expect(screen.getByText(/8 Cores/i)).toBeInTheDocument();
    expect(screen.getByText(/1800 MHz/i)).toBeInTheDocument();

    // Verify Battery
    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByText(/3.5 W/i)).toBeInTheDocument();
    expect(screen.getByText(/4.12 V/i)).toBeInTheDocument();

    // Verify Network
    expect(screen.getByText(/Interface: wlan0/i)).toBeInTheDocument();

    // Verify async REST load
    expect(await screen.findByText(/58G/i)).toBeInTheDocument();
    expect(await screen.findByText('python3')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
  });
});
