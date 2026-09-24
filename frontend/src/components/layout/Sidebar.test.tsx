import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { api } from '../../api/client';

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
  },
}));

describe('Sidebar Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders branding and all navigation links', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      model: 'Raspberry Pi 4',
      os_name: 'Alpine Linux 3.20',
    });

    render(
      <MemoryRouter initialEntries={['/']}>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText('Lavender')).toBeInTheDocument();
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Services')).toBeInTheDocument();
    expect(screen.getByText('Processes')).toBeInTheDocument();
    expect(screen.getByText('Storage')).toBeInTheDocument();
    expect(screen.getByText('Network')).toBeInTheDocument();
    expect(screen.getByText('Packages')).toBeInTheDocument();
    expect(screen.getByText('Users')).toBeInTheDocument();
    expect(screen.getByText('Power')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Raspberry Pi 4')).toBeInTheDocument();
      expect(screen.getByText('Alpine Linux 3.20')).toBeInTheDocument();
    });
  });

  it('toggles collapse state and persists to localStorage', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(null);

    render(
      <MemoryRouter initialEntries={['/']}>
        <Sidebar />
      </MemoryRouter>
    );

    const toggleBtn = await screen.findByRole('button', { name: /collapse sidebar/i });
    expect(localStorage.getItem('lavender_sidebar_collapsed')).toBe('false');

    act(() => {
      fireEvent.click(toggleBtn);
    });
    expect(localStorage.getItem('lavender_sidebar_collapsed')).toBe('true');

    const expandBtn = screen.getByRole('button', { name: /expand sidebar/i });
    act(() => {
      fireEvent.click(expandBtn);
    });
    expect(localStorage.getItem('lavender_sidebar_collapsed')).toBe('false');
  });
});
