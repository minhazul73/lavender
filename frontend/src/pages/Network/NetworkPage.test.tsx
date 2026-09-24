import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { NetworkPage } from './NetworkPage';
import { api } from '../../api/client';
import { ToastProvider } from '../../context/ToastContext';

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('NetworkPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockNetworkData = {
    interfaces: [
      { name: 'eth0', ip: '192.168.1.150', mac: 'b8:27:eb:11:22:33', state: 'UP', speed: '1000 Mb/s' },
      { name: 'wlan0', ip: '192.168.1.151', mac: 'b8:27:eb:44:55:66', state: 'UP', speed: '54 Mb/s' },
    ],
    wifi: {
      connected: true,
      ssid: 'LavenderNet-5G',
      signal: 82,
      networks: [
        { ssid: 'LavenderNet-5G', signal: 82, security: 'WPA2-PSK', frequency: '5180 MHz' },
        { ssid: 'GuestWifi', signal: 45, security: 'Open', frequency: '2412 MHz' },
      ],
    },
    dns: ['1.1.1.1', '8.8.8.8'],
    dns_details: {},
    gateways: [],
    summary: {},
  };

  it('renders network interfaces and active WiFi connection', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockNetworkData);

    render(
      <ToastProvider>
        <MemoryRouter>
          <NetworkPage />
        </MemoryRouter>
      </ToastProvider>
    );

    expect(await screen.findByText('eth0')).toBeInTheDocument();
    expect(screen.getByText('wlan0')).toBeInTheDocument();
    expect(screen.getByText('192.168.1.150')).toBeInTheDocument();
    expect(screen.getByText('b8:27:eb:11:22:33')).toBeInTheDocument();
    expect(screen.getAllByText('LavenderNet-5G').length).toBeGreaterThan(0);
    expect(screen.getByText('GuestWifi')).toBeInTheDocument();
  });

  it('triggers WiFi scan and displays updated networks', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockNetworkData);
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      networks: [
        { ssid: 'NewHotspot', signal: 95, security: 'WPA3', frequency: '5GHz' },
      ],
    });

    render(
      <ToastProvider>
        <MemoryRouter>
          <NetworkPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findByText('eth0');

    const scanBtn = screen.getByRole('button', { name: /Scan Wireless Networks/i });
    act(() => {
      fireEvent.click(scanBtn);
    });

    expect(await screen.findByText('NewHotspot')).toBeInTheDocument();
    expect(screen.getByText('WPA3')).toBeInTheDocument();
  });

  it('executes Ping test and displays statistics', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/ping')) {
        return Promise.resolve({
          target: '1.1.1.1',
          transmitted: 3,
          received: 3,
          packet_loss: 0,
          avg_latency_ms: 12.45,
          success: true,
        });
      }
      return Promise.resolve(mockNetworkData);
    });

    render(
      <ToastProvider>
        <MemoryRouter>
          <NetworkPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findByText('eth0');

    const pingBtn = screen.getByRole('button', { name: /^Ping$/i });
    act(() => {
      fireEvent.click(pingBtn);
    });

    expect(await screen.findByText(/Avg Latency: 12.45 ms/i)).toBeInTheDocument();
    expect(screen.getByText(/Transmitted: 3 \| Received: 3/i)).toBeInTheDocument();
    expect(screen.getByText('Reachable')).toBeInTheDocument();
  });

  it('executes DNS query and displays resolved IP', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/dns-query')) {
        return Promise.resolve({
          domain: 'google.com',
          resolved_ip: '142.250.190.46',
          latency_ms: 18.2,
          success: true,
        });
      }
      return Promise.resolve(mockNetworkData);
    });

    render(
      <ToastProvider>
        <MemoryRouter>
          <NetworkPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findByText('eth0');

    const dnsBtn = screen.getByRole('button', { name: /^Resolve$/i });
    act(() => {
      fireEvent.click(dnsBtn);
    });

    expect(await screen.findByText(/IP Address: 142.250.190.46/i)).toBeInTheDocument();
    expect(screen.getByText(/Query Time: 18.2 ms/i)).toBeInTheDocument();
  });
});
