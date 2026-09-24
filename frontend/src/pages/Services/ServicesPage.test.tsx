import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ServicesPage } from './ServicesPage';
import { api } from '../../api/client';
import { ToastProvider } from '../../context/ToastContext';

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('ServicesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockServices = [
    {
      unit: 'sshd.service',
      description: 'OpenSSH server daemon',
      scope: 'system',
      load: 'loaded',
      active: 'active',
      sub: 'running',
    },
    {
      unit: 'lavender.service',
      description: 'Lavender Linux Dashboard',
      scope: 'system',
      load: 'loaded',
      active: 'active',
      sub: 'running',
    },
    {
      unit: 'user-agent.service',
      description: 'User notification agent',
      scope: 'user',
      load: 'loaded',
      active: 'inactive',
      sub: 'dead',
    },
  ];

  it('renders services list with name, scope and status', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      services: mockServices,
      count: 3,
    });

    render(
      <ToastProvider>
        <MemoryRouter>
          <ServicesPage />
        </MemoryRouter>
      </ToastProvider>
    );

    expect(await screen.findByText('sshd.service')).toBeInTheDocument();
    expect(screen.getByText('lavender.service')).toBeInTheDocument();
    expect(screen.getByText('user-agent.service')).toBeInTheDocument();
    expect(screen.getByText('OpenSSH server daemon')).toBeInTheDocument();
  });

  it('filters services based on search query', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      services: mockServices,
      count: 3,
    });

    render(
      <ToastProvider>
        <MemoryRouter>
          <ServicesPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findByText('sshd.service');

    const searchInput = screen.getByPlaceholderText(/search services/i);
    fireEvent.change(searchInput, { target: { value: 'lavender' } });

    expect(screen.getByText('lavender.service')).toBeInTheDocument();
    expect(screen.queryByText('sshd.service')).toBeNull();
  });

  it('filters services based on scope filter', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      services: mockServices,
      count: 3,
    });

    render(
      <ToastProvider>
        <MemoryRouter>
          <ServicesPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findByText('sshd.service');

    const scopeSelect = screen.getByDisplayValue('All Services');
    fireEvent.change(scopeSelect, { target: { value: 'user' } });

    expect(screen.getByText('user-agent.service')).toBeInTheDocument();
    expect(screen.queryByText('sshd.service')).toBeNull();
  });

  it('prompts confirm modal on restart action and posts to API', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      services: mockServices,
      count: 3,
    });
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      action: 'restart',
      service: 'sshd.service',
    });

    render(
      <ToastProvider>
        <MemoryRouter>
          <ServicesPage />
        </MemoryRouter>
      </ToastProvider>
    );

    await screen.findByText('sshd.service');

    const restartBtns = screen.getAllByTitle('Restart Service');
    act(() => {
      fireEvent.click(restartBtns[0]);
    });

    // Modal appears
    expect(await screen.findByText('RESTART Service')).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to restart unit 'sshd.service'/i)).toBeInTheDocument();

    const dialog = screen.getByRole('dialog');
    const confirmBtn = within(dialog).getByRole('button', { name: /restart/i });
    act(() => {
      fireEvent.click(confirmBtn);
    });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/api/system/services/action', {
        service: 'sshd.service',
        action: 'restart',
        user: false,
      });
    });
  });
});
