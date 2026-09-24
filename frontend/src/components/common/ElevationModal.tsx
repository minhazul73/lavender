import React, { useState } from 'react';
import { Modal } from './Modal';
import { useAuth } from '../../context/AuthContext';
import { ShieldAlert, KeyRound, Loader2 } from 'lucide-react';

export const ElevationModal: React.FC = () => {
  const { isElevationModalOpen, closeElevationModal, elevate, session } = useAuth();
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) {
      setError('Password is required');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const ok = await elevate(password);
      if (ok) {
        setPassword('');
      } else {
        setError('Elevation failed. Please verify credentials.');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Invalid administrator password';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setPassword('');
    setError(null);
    closeElevationModal(false);
  };

  return (
    <Modal
      isOpen={isElevationModalOpen}
      onClose={handleClose}
      title={
        <span style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#c4b5fd' }}>
          <ShieldAlert size={20} color="#a78bfa" /> Administrative Elevation Required
        </span>
      }
    >
      <form onSubmit={handleSubmit}>
        <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          The requested action requires elevated Linux privileges. Enter password for{' '}
          <strong style={{ color: 'var(--text-primary)' }}>{session?.username || 'user'}</strong>:
        </p>

        {error && (
          <div
            style={{
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#f87171',
              padding: '10px 14px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.85rem',
              marginBottom: '16px',
            }}
          >
            {error}
          </div>
        )}

        <div className="form-group">
          <label className="form-label" htmlFor="elevate-password">
            Sudo / System Password
          </label>
          <div style={{ position: 'relative' }}>
            <input
              id="elevate-password"
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password to elevate"
              autoFocus
              disabled={loading}
              style={{ paddingLeft: '36px' }}
            />
            <KeyRound
              size={16}
              style={{
                position: 'absolute',
                left: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-muted)',
              }}
            />
          </div>
        </div>

        <div className="modal-footer">
          <button
            type="button"
            onClick={handleClose}
            className="btn btn-secondary"
            disabled={loading}
          >
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" /> Verifying...
              </>
            ) : (
              'Elevate Access'
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
};
