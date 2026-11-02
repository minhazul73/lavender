import React from 'react';
import { Modal } from '../../components/common/Modal';
import { Lock } from 'lucide-react';

export interface PasswordModalProps {
  selectedPassUser: string | null;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (e: React.FormEvent) => Promise<void>;
  newPassword: string;
  setNewPassword: (v: string) => void;
  confirmPassword: string;
  setConfirmPassword: (v: string) => void;
  passLoading: boolean;
}

export const PasswordModal: React.FC<PasswordModalProps> = ({
  selectedPassUser,
  isOpen,
  onClose,
  onSubmit,
  newPassword,
  setNewPassword,
  confirmPassword,
  setConfirmPassword,
  passLoading,
}) => {
  if (!isOpen || !selectedPassUser) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Lock size={18} color="var(--purple)" /> Change Password: {selectedPassUser}
        </span>
      }
    >
      <form onSubmit={onSubmit}>
        <div className="form-group" style={{ marginBottom: '14px' }}>
          <label className="form-label" htmlFor="new-pwd-input">
            New System Password
          </label>
          <input
            id="new-pwd-input"
            type="password"
            className="form-input"
            placeholder="Enter new password (min 4 chars)"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            autoFocus
            disabled={passLoading}
            required
          />
        </div>

        <div className="form-group" style={{ marginBottom: '14px' }}>
          <label className="form-label" htmlFor="confirm-pwd-input">
            Confirm Password
          </label>
          <input
            id="confirm-pwd-input"
            type="password"
            className="form-input"
            placeholder="Repeat new password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            disabled={passLoading}
          />
        </div>

        <div className="modal-footer">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
            disabled={passLoading}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={passLoading || newPassword.length < 4}
          >
            {passLoading ? 'Updating…' : 'Update Password'}
          </button>
        </div>
      </form>
    </Modal>
  );
};
