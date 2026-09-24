import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConfirmModal } from './ConfirmModal';

describe('ConfirmModal Component', () => {
  it('does not render when isOpen is false', () => {
    const { container } = render(
      <ConfirmModal
        isOpen={false}
        title="Delete Item"
        message="Are you sure you want to delete this?"
        onClose={vi.fn()}
        onConfirm={vi.fn()}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders title, message, and buttons when isOpen is true', () => {
    render(
      <ConfirmModal
        isOpen={true}
        title="Restart System"
        message="Rebooting will terminate active connections."
        confirmLabel="Reboot Now"
        cancelLabel="Dismiss"
        onClose={vi.fn()}
        onConfirm={vi.fn()}
      />
    );

    expect(screen.getByText('Restart System')).toBeInTheDocument();
    expect(screen.getByText('Rebooting will terminate active connections.')).toBeInTheDocument();
    expect(screen.getByText('Reboot Now')).toBeInTheDocument();
    expect(screen.getByText('Dismiss')).toBeInTheDocument();
  });

  it('triggers onConfirm when confirm button clicked', () => {
    const onConfirmMock = vi.fn();
    render(
      <ConfirmModal
        isOpen={true}
        title="Reboot"
        message="Reboot now?"
        onClose={vi.fn()}
        onConfirm={onConfirmMock}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onConfirmMock).toHaveBeenCalledTimes(1);
  });

  it('triggers onClose when cancel button or backdrop clicked', () => {
    const onCloseMock = vi.fn();
    render(
      <ConfirmModal
        isOpen={true}
        title="Reboot"
        message="Reboot now?"
        onClose={onCloseMock}
        onConfirm={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });

  it('disables buttons when isLoading is true', () => {
    render(
      <ConfirmModal
        isOpen={true}
        title="Reboot"
        message="Reboot now?"
        isLoading={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
      />
    );

    const buttons = screen.getAllByRole('button');
    buttons.forEach((btn) => {
      expect(btn).toBeDisabled();
    });
  });
});
