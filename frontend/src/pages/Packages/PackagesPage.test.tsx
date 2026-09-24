import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { PackagesPage } from './PackagesPage';
import { api } from '../../api/client';
import { ToastProvider } from '../../context/ToastContext';

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('PackagesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockPackagesData = {
    backend: 'apk',
    backend_name: 'Alpine Package Keeper',
    backend_short: 'apk',
    installed_count: 350,
    upgradable_count: 2,
    upgradable: [
      { name: 'openssl', version: '3.1.4-r0', new_version: '3.1.5-r0', description: 'Cryptography toolkit' },
      { name: 'curl', version: '8.5.0-r0', new_version: '8.6.0-r0', description: 'Command line URL transfer' },
    ],
    installed: [
      { name: 'busybox', version: '1.36.1-r15', description: 'Swiss Army Knife of Embedded Linux' },
      { name: 'python3', version: '3.11.8-r0', description: 'Python programming language' },
    ],
  };

  it('renders package backend, upgradable count, and pending upgrades', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockPackagesData);

    render(
      <ToastProvider>
        <MemoryRouter>
          <PackagesPage />
        </MemoryRouter>
      </ToastProvider>
    );

    expect(await screen.findByText('Alpine Package Keeper')).toBeInTheDocument();
    expect(screen.getByText('openssl')).toBeInTheDocument();
    expect(screen.getByText('3.1.5-r0')).toBeInTheDocument();
    expect(screen.getByText('curl')).toBeInTheDocument();
    expect(screen.getByText('8.6.0-r0')).toBeInTheDocument();
  });

  it('opens confirmation modal and triggers upgrade-all', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockPackagesData);
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      action: 'upgrade',
    });

    render(
      <ToastProvider>
        <MemoryRouter>
          <PackagesPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findByText('Alpine Package Keeper');

    const upgradeAllBtn = screen.getByRole('button', { name: /Upgrade All \(2\)/i });
    act(() => {
      fireEvent.click(upgradeAllBtn);
    });

    // Confirmation modal appears
    expect(await screen.findByText(/UPGRADE-ALL Package/i)).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to upgrade all pending system packages\?/i)).toBeInTheDocument();

    const dialog = screen.getByRole('dialog');
    const confirmBtn = within(dialog).getByRole('button', { name: /^Upgrade All$/i });

    act(() => {
      fireEvent.click(confirmBtn);
    });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/api/packages/upgrade');
    });
  });

  it('searches remote repositories and displays installable packages', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/search')) {
        return Promise.resolve({
          results: [
            { name: 'htop', version: '3.3.0', description: 'Interactive process viewer', installed: false },
          ],
        });
      }
      return Promise.resolve(mockPackagesData);
    });

    render(
      <ToastProvider>
        <MemoryRouter>
          <PackagesPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findByText('Alpine Package Keeper');

    const searchInput = screen.getByPlaceholderText(/search online repositories/i);
    fireEvent.change(searchInput, { target: { value: 'htop' } });

    const searchBtn = screen.getByRole('button', { name: /Search Repos/i });
    act(() => {
      fireEvent.click(searchBtn);
    });

    expect(await screen.findByText('htop')).toBeInTheDocument();
    expect(screen.getByText('Interactive process viewer')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Install$/i })).toBeInTheDocument();
  });
});
