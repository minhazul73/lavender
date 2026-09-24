import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { StoragePage } from './StoragePage';
import { api } from '../../api/client';
import { ToastProvider } from '../../context/ToastContext';

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('StoragePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockStorageData = {
    disks: [
      {
        mount_point: '/',
        filesystem: '/dev/mmcblk0p2',
        size: '29.1G',
        used: '4.2G',
        available: '23.4G',
        use_percent: '16%',
      },
      {
        mount_point: '/mnt/usb-drive',
        filesystem: '/dev/sda1',
        size: '118G',
        used: '45G',
        available: '67G',
        use_percent: '40%',
      },
    ],
  };

  it('renders mounted partition cards and summary table', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockStorageData);

    render(
      <ToastProvider>
        <MemoryRouter>
          <StoragePage />
        </MemoryRouter>
      </ToastProvider>
    );

    expect((await screen.findAllByText('/mnt/usb-drive')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('/dev/mmcblk0p2').length).toBeGreaterThan(0);
    expect(screen.getAllByText('/dev/sda1').length).toBeGreaterThan(0);
    expect(screen.getAllByText('29.1G').length).toBeGreaterThan(0);
    expect(screen.getAllByText('118G').length).toBeGreaterThan(0);
  });

  it('allows unmounting non-root drive via confirmation modal', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockStorageData);
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      message: 'Unmounted successfully',
    });

    render(
      <ToastProvider>
        <MemoryRouter>
          <StoragePage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findAllByText('/mnt/usb-drive');

    const unmountBtn = screen.getByRole('button', { name: /unmount/i });
    act(() => {
      fireEvent.click(unmountBtn);
    });

    // Confirmation modal appears
    expect(await screen.findByText(/Unmount Filesystem/i)).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to unmount '\/mnt\/usb-drive'/i)).toBeInTheDocument();

    const dialog = screen.getByRole('dialog');
    const confirmBtn = within(dialog).getByRole('button', { name: /Unmount Partition/i });

    act(() => {
      fireEvent.click(confirmBtn);
    });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        expect.stringContaining('/api/storage/unmount?mount_point=%2Fmnt%2Fusb-drive')
      );
    });
  });
});
