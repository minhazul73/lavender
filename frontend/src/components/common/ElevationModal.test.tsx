import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ElevationModal } from './ElevationModal';
import { useAuth } from '../../context/AuthContext';

vi.mock('../../context/AuthContext', () => ({
  useAuth: vi.fn(),
}));

describe('ElevationModal Component', () => {
  const mockElevate = vi.fn();
  const mockCloseElevationModal = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when isElevationModalOpen is false', () => {
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      isElevationModalOpen: false,
      closeElevationModal: mockCloseElevationModal,
      elevate: mockElevate,
      session: { username: 'testuser' },
    });

    const { container } = render(<ElevationModal />);
    expect(container.firstChild).toBeNull();
  });

  it('renders form and submits password to elevate', async () => {
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      isElevationModalOpen: true,
      closeElevationModal: mockCloseElevationModal,
      elevate: mockElevate.mockResolvedValue(true),
      session: { username: 'testuser' },
    });

    render(<ElevationModal />);

    expect(screen.getByText(/Administrative Elevation Required/i)).toBeInTheDocument();
    expect(screen.getByText(/testuser/i)).toBeInTheDocument();

    const input = screen.getByLabelText(/Sudo \/ System Password/i);
    fireEvent.change(input, { target: { value: 'mypassword123' } });

    fireEvent.click(screen.getByRole('button', { name: /Elevate Access/i }));

    await waitFor(() => {
      expect(mockElevate).toHaveBeenCalledWith('mypassword123');
    });
  });

  it('displays error message when elevation fails', async () => {
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      isElevationModalOpen: true,
      closeElevationModal: mockCloseElevationModal,
      elevate: mockElevate.mockRejectedValue(new Error('Incorrect password')),
      session: { username: 'testuser' },
    });

    render(<ElevationModal />);

    const input = screen.getByLabelText(/Sudo \/ System Password/i);
    fireEvent.change(input, { target: { value: 'wrongpassword' } });

    fireEvent.click(screen.getByRole('button', { name: /Elevate Access/i }));

    expect(await screen.findByText('Incorrect password')).toBeInTheDocument();
  });

  it('calls closeElevationModal(false) when cancel button clicked', () => {
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      isElevationModalOpen: true,
      closeElevationModal: mockCloseElevationModal,
      elevate: mockElevate,
      session: { username: 'testuser' },
    });

    render(<ElevationModal />);

    fireEvent.click(screen.getByRole('button', { name: /Cancel/i }));
    expect(mockCloseElevationModal).toHaveBeenCalledWith(false);
  });
});
