import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LoginPage } from './LoginPage';
import { useAuth } from '../../context/AuthContext';

vi.mock('../../context/AuthContext', () => ({
  useAuth: vi.fn(),
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('LoginPage', () => {
  const mockLogin = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders login form with title and subtitle', () => {
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      login: mockLogin,
      session: null,
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    expect(screen.getByText('Lavender')).toBeInTheDocument();
    expect(screen.getByText('Sign in with your Linux system credentials')).toBeInTheDocument();
    expect(screen.getByLabelText(/Username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Password$/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sign In/i })).toBeInTheDocument();
  });

  it('validates empty inputs on submit', async () => {
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      login: mockLogin,
      session: null,
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

    expect(await screen.findByText('Username and password are required')).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('submits credentials and navigates on success', async () => {
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      login: mockLogin.mockResolvedValue({ success: true, redirect: '/' }),
      session: null,
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/Username/i), { target: { value: 'alice' } });
    fireEvent.change(screen.getByLabelText(/^Password$/i), { target: { value: 'secretpass' } });

    fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('alice', 'secretpass', '/');
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });

  it('displays alert on authentication failure', async () => {
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      login: mockLogin.mockRejectedValue(new Error('Invalid PAM credentials')),
      session: null,
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/Username/i), { target: { value: 'alice' } });
    fireEvent.change(screen.getByLabelText(/^Password$/i), { target: { value: 'wrongpass' } });

    fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

    expect(await screen.findByText('Invalid PAM credentials')).toBeInTheDocument();
  });

  it('toggles password input visibility', () => {
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      login: mockLogin,
      session: null,
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    const passwordInput = screen.getByLabelText(/^Password$/i) as HTMLInputElement;
    expect(passwordInput.type).toBe('password');

    const toggleBtn = screen.getByRole('button', { name: /show password/i });
    fireEvent.click(toggleBtn);
    expect(passwordInput.type).toBe('text');

    const hideBtn = screen.getByRole('button', { name: /hide password/i });
    fireEvent.click(hideBtn);
    expect(passwordInput.type).toBe('password');
  });
});
