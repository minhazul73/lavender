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

    // Verify Battery percentage, thermal sensor, and memory
    expect(screen.getAllByText('85%').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('42.5°C')).toBeInTheDocument();
    expect(screen.getAllByText('50%').length).toBeGreaterThanOrEqual(1);

    // Verify CPU card
    expect(screen.getByText('1.45')).toBeInTheDocument();
    expect(screen.getByText(/8 Cores/i)).toBeInTheDocument();
    expect(screen.getByText(/1800 MHz/i)).toBeInTheDocument();

    // Verify Battery
    expect(screen.getByText(/3.50 W|3.5 W/i)).toBeInTheDocument();
    expect(screen.getByText(/4.12 V/i)).toBeInTheDocument();

    // Verify Network
    expect(screen.getByText('wlan0')).toBeInTheDocument();

    // Verify async REST load
    expect(await screen.findByText(/58G/i)).toBeInTheDocument();
    expect(await screen.findByText(/python3/i)).toBeInTheDocument();
    expect(screen.getAllByText('Active').length).toBeGreaterThanOrEqual(1);
  });

  it('renders correctly with legacy disk keys without throwing replace error', async () => {
    (useSSE as ReturnType<typeof vi.fn>).mockReturnValue({
      data: null,
      status: 'connected',
    });

    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/storage')) {
        return Promise.resolve({
          disks: [
            {
              mount: '/data',
              fs: '/dev/nvme0n1p1',
              size: '500G',
              used: '120G',
              avail: '380G',
              use_pct: '24%',
              pct_num: 24,
            },
          ],
        });
      }
      return Promise.resolve({});
    });

    render(
      <MemoryRouter>
        <OverviewPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('/data')).toBeInTheDocument();
    expect(screen.getByText(/120G \/ 500G/i)).toBeInTheDocument();
    expect(screen.getAllByText(/24%/i).length).toBeGreaterThanOrEqual(1);
  });

  it('renders structured log objects without throwing React child error', async () => {
    (useSSE as ReturnType<typeof vi.fn>).mockReturnValue({
      data: null,
      status: 'connected',
    });

    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/logs')) {
        return Promise.resolve({
          logs: [
            {
              timestamp: '23:59:01',
              message: 'Session created for user admin',
              service: 'lavender',
              level: 'info',
            },
          ],
        });
      }
      return Promise.resolve({});
    });

    render(
      <MemoryRouter>
        <OverviewPage />
      </MemoryRouter>
    );

    expect(await screen.findByText(/Session created for user admin/i)).toBeInTheDocument();
    expect(screen.getByText(/lavender:/i)).toBeInTheDocument();
    expect(screen.getByText(/23:59:01/i)).toBeInTheDocument();
  });

  it('formats ISO log timestamps into readable local client time', async () => {
    (useSSE as ReturnType<typeof vi.fn>).mockReturnValue({
      data: null,
      status: 'connected',
    });

    const now = new Date();
    const isoString = now.toISOString();
    const expectedTime = now.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });

    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/logs')) {
        return Promise.resolve({
          logs: [
            {
              timestamp: isoString,
              message: 'Daemon sync completed',
              service: 'systemd',
              level: 'info',
            },
          ],
        });
      }
      return Promise.resolve({});
    });

    render(
      <MemoryRouter>
        <OverviewPage />
      </MemoryRouter>
    );

    expect(await screen.findByText(/Daemon sync completed/i)).toBeInTheDocument();
    expect(screen.getByText(/systemd:/i)).toBeInTheDocument();
    expect(screen.getByText(expectedTime)).toBeInTheDocument();
  });
});

// Characterization: sparkline helpers
// These functions are copied verbatim from OverviewPage.tsx for testing.
// When T-030 extracts them to utils/sparkline.ts, these tests will move there.
function normalizeBuffer(buf: number[], targetLen = 30): number[] {
  if (!buf || buf.length === 0) return new Array(targetLen).fill(0);
  if (buf.length >= targetLen) return buf.slice(buf.length - targetLen);
  const pad = new Array(targetLen - buf.length).fill(buf[0]);
  return [...pad, ...buf];
}

function buildSparkPaths(
  buf: number[],
  w = 100,
  h = 32,
  minRange = 10,
  clampMin?: number,
  clampMax?: number
): { line: string; area: string } {
  if (!buf || buf.length < 2) return { line: '', area: '' };

  let min = Math.min(...buf);
  let max = Math.max(...buf);

  if (clampMin !== undefined) min = Math.min(min, clampMin);
  if (clampMax !== undefined) max = Math.max(max, clampMax);

  const currentRange = max - min;
  if (currentRange < minRange) {
    const padRange = (minRange - currentRange) / 2;
    min = clampMin !== undefined ? Math.max(clampMin, min - padRange) : min - padRange;
    max = clampMax !== undefined ? Math.min(clampMax, max + padRange) : max + padRange;
  }
  const range = max - min || 1;
  const pad = h * 0.08;

  const pts = buf.map((v, i) => ({
    x: parseFloat(((i / (buf.length - 1)) * w).toFixed(2)),
    y: parseFloat((pad + (1 - (v - min) / range) * (h - pad * 2)).toFixed(2)),
  }));

  const t = 0.4;
  const ctrlPts = (
    p0: { x: number; y: number },
    p1: { x: number; y: number },
    p2: { x: number; y: number },
    p3: { x: number; y: number }
  ) => ({
    cp1x: p1.x + (p2.x - p0.x) * t,
    cp1y: p1.y + (p2.y - p0.y) * t,
    cp2x: p2.x - (p3.x - p1.x) * t,
    cp2y: p2.y - (p3.y - p1.y) * t,
  });

  let line = `M${pts[0].x},${pts[0].y}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(pts.length - 1, i + 2)];
    const c = ctrlPts(p0, p1, p2, p3);
    line += ` C${c.cp1x.toFixed(2)},${c.cp1y.toFixed(2)} ${c.cp2x.toFixed(2)},${c.cp2y.toFixed(2)} ${p2.x.toFixed(2)},${p2.y.toFixed(2)}`;
  }

  const last = pts[pts.length - 1];
  const area = `${line} L${last.x},${h} L${pts[0].x},${h} Z`;
  return { line, area };
}

describe('normalizeBuffer', () => {
  it('pads a short buffer by repeating oldest element', () => {
    const result = normalizeBuffer([1, 2, 3], 5);
    expect(result).toHaveLength(5);
    expect(result[0]).toBe(1);
    expect(result[4]).toBe(3);
  });
  it('returns zeros for empty or null buffer', () => {
    const empty = normalizeBuffer([], 5);
    expect(empty).toEqual([0, 0, 0, 0, 0]);
  });
  it('truncates a buffer longer than targetLen', () => {
    const long = Array.from({ length: 40 }, (_, i) => i);
    const result = normalizeBuffer(long, 30);
    expect(result).toHaveLength(30);
    expect(result[0]).toBe(10);
    expect(result[29]).toBe(39);
  });
  it('returns buffer unchanged if already targetLen', () => {
    const buf = Array(30).fill(5);
    expect(normalizeBuffer(buf, 30)).toEqual(buf);
  });
});

describe('buildSparkPaths', () => {
  it('returns area and line string paths', () => {
    const buf = Array(30).fill(50);
    const result = buildSparkPaths(buf, 200, 40);
    expect(typeof result.area).toBe('string');
    expect(typeof result.line).toBe('string');
    expect(result.area.startsWith('M')).toBe(true);
  });
  it('handles empty/zero buffer without throwing', () => {
    const result = buildSparkPaths(Array(30).fill(0), 200, 40);
    expect(result.line).toBeTruthy();
  });
  it('returns empty strings for buffer with less than 2 points', () => {
    expect(buildSparkPaths([])).toEqual({ line: '', area: '' });
    expect(buildSparkPaths([42])).toEqual({ line: '', area: '' });
  });
});


