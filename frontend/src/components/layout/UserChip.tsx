import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { ConfirmModal } from '../common/ConfirmModal';
import { ShieldCheck, LogOut, LogIn, Lock } from 'lucide-react';
import { Link } from 'react-router-dom';

export const UserChip: React.FC = () => {
  const { session, logout, isElevated, dropElevation, openElevationModal } = useAuth();
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  if (!session) {
    return (
      <Link
        to="/login"
        className="btn btn-sm btn-primary"
        style={{ textDecoration: 'none' }}
        id="btn-login-topbar"
      >
        <LogIn size={14} />
        <span>Sign In</span>
      </Link>
    );
  }

  const initial = session.username ? session.username[0].toUpperCase() : 'U';

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
    } finally {
      setIsLoggingOut(false);
      setShowLogoutConfirm(false);
    }
  };

  return (
    <>
      <div
        className="user-chip"
        id="user-chip"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          padding: '4px 8px 4px 6px',
          background: 'rgba(15, 23, 42, 0.65)',
          backdropFilter: 'blur(8px)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-full)',
          fontSize: '0.84rem',
        }}
      >
        {/* Avatar */}
        <div
          className="user-avatar"
          title={`Logged in as ${session.username}`}
          style={{
            width: '28px',
            height: '28px',
            borderRadius: '50%',
            background: 'var(--grad-lavender)',
            color: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 600,
            fontSize: '0.85rem',
            boxShadow: '0 0 8px var(--lavender-glow)',
          }}
        >
          {initial}
        </div>

        {/* Username */}
        <span
          className="user-name"
          style={{ fontWeight: 500, color: 'var(--text-primary)' }}
        >
          {session.username}
        </span>

        {/* Elevation status */}
        {isElevated ? (
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <span
              className="badge badge-success"
              id="admin-badge"
              title="Administrative privileges active"
              style={{ fontSize: '0.72rem', padding: '2px 8px' }}
            >
              <ShieldCheck size={12} /> Admin
            </span>
            {session.username !== 'root' && session.uid !== 0 && (
              <button
                type="button"
                onClick={dropElevation}
                className="btn btn-xs btn-ghost"
                title="Turn off administrative access"
                style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}
              >
                Turn off
              </button>
            )}
          </div>
        ) : session.can_elevate ? (
          <button
            type="button"
            onClick={() => openElevationModal()}
            className="btn btn-xs btn-secondary"
            title={`Elevate permissions for ${session.username}`}
            style={{
              padding: '2px 8px',
              fontSize: '0.72rem',
              borderRadius: 'var(--radius-full)',
            }}
          >
            <Lock size={11} /> Admin
          </button>
        ) : null}

        {/* Sign out */}
        <button
          type="button"
          onClick={() => setShowLogoutConfirm(true)}
          className="btn btn-xs btn-ghost btn-icon"
          title="Sign out"
          style={{ color: 'var(--text-muted)', marginLeft: '2px' }}
          id="btn-logout"
          aria-label="Sign out"
        >
          <LogOut size={14} />
        </button>
      </div>

      <ConfirmModal
        isOpen={showLogoutConfirm}
        onClose={() => setShowLogoutConfirm(false)}
        onConfirm={handleLogout}
        title="Sign Out"
        message={`Are you sure you want to sign out from account "${session.username}"?`}
        confirmLabel="Sign Out"
        cancelLabel="Stay"
        isDanger={false}
        isLoading={isLoggingOut}
      />
    </>
  );
};
