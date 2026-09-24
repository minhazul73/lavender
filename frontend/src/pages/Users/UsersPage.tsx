import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../api/client';
import { UsersOverviewResponse, UserItem, UserSessionItem } from '../../api/types';
import { useToast } from '../../context/ToastContext';
import { Modal } from '../../components/common/Modal';
import { ConfirmModal } from '../../components/common/ConfirmModal';
import {
  Users,
  Shield,
  Key,
  Lock,
  Terminal,
  RefreshCw,
  Trash2,
  Plus,
  XCircle,
} from 'lucide-react';

export const UsersPage: React.FC = () => {
  const { addToast } = useToast();
  const [data, setData] = useState<UsersOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Terminate session state
  const [pendingTerminate, setPendingTerminate] = useState<UserSessionItem | null>(null);
  const [terminateLoading, setTerminateLoading] = useState(false);

  // SSH Keys Modal state
  const [selectedSshUser, setSelectedSshUser] = useState<string | null>(null);
  const [sshKeys, setSshKeys] = useState<string[]>([]);
  const [sshLoading, setSshLoading] = useState(false);
  const [newSshKey, setNewSshKey] = useState('');
  const [addKeyLoading, setAddKeyLoading] = useState(false);

  // Password Modal state
  const [selectedPassUser, setSelectedPassUser] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState('');
  const [passLoading, setPassLoading] = useState(false);

  const loadUsers = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const res = await api.get<UsersOverviewResponse>('/api/users');
      setData(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch users overview';
      addToast(msg, 'error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [addToast]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  // Terminate Session
  const handleConfirmTerminate = async () => {
    if (!pendingTerminate) return;
    setTerminateLoading(true);
    try {
      const res = await api.post<{ success: boolean; message?: string }>('/api/users/session/terminate', {
        tty: pendingTerminate.tty,
      });
      if (res.success) {
        addToast(res.message || `Session on ${pendingTerminate.tty} terminated`, 'success');
        setPendingTerminate(null);
        await loadUsers(true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to terminate session';
      addToast(msg, 'error');
    } finally {
      setTerminateLoading(false);
    }
  };

  // Open SSH Keys Modal
  const handleOpenSshModal = async (username: string) => {
    setSelectedSshUser(username);
    setSshLoading(true);
    setNewSshKey('');
    try {
      const res = await api.get<{ keys: string[] }>(`/api/users/${encodeURIComponent(username)}/ssh-keys`);
      setSshKeys(res.keys || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load SSH keys';
      addToast(msg, 'error');
      setSelectedSshUser(null);
    } finally {
      setSshLoading(false);
    }
  };

  // Add SSH Key
  const handleAddSshKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSshUser || !newSshKey.trim()) return;
    setAddKeyLoading(true);
    try {
      const res = await api.post<{ success: boolean }>(`/api/users/${encodeURIComponent(selectedSshUser)}/ssh-keys`, {
        key: newSshKey.trim(),
      });
      if (res.success) {
        addToast('SSH key added', 'success');
        setNewSshKey('');
        const updated = await api.get<{ keys: string[] }>(`/api/users/${encodeURIComponent(selectedSshUser)}/ssh-keys`);
        setSshKeys(updated.keys || []);
        await loadUsers(true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to add SSH key';
      addToast(msg, 'error');
    } finally {
      setAddKeyLoading(false);
    }
  };

  // Delete SSH Key
  const handleDeleteSshKey = async (index: number) => {
    if (!selectedSshUser) return;
    try {
      const res = await api.delete<{ success: boolean }>(
        `/api/users/${encodeURIComponent(selectedSshUser)}/ssh-keys/${index}`
      );
      if (res.success) {
        addToast('SSH key removed', 'success');
        const updated = await api.get<{ keys: string[] }>(`/api/users/${encodeURIComponent(selectedSshUser)}/ssh-keys`);
        setSshKeys(updated.keys || []);
        await loadUsers(true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to remove SSH key';
      addToast(msg, 'error');
    }
  };

  // Change Password
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPassUser || !newPassword) return;
    setPassLoading(true);
    try {
      const res = await api.post<{ success: boolean }>(
        `/api/users/${encodeURIComponent(selectedPassUser)}/password`,
        { new_password: newPassword }
      );
      if (res.success) {
        addToast(`Password updated for ${selectedPassUser}`, 'success');
        setSelectedPassUser(null);
        setNewPassword('');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update password';
      addToast(msg, 'error');
    } finally {
      setPassLoading(false);
    }
  };

  const humanUsers: UserItem[] = data?.human_users || [];
  const activeSessions: UserSessionItem[] = data?.active_sessions || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* ── Toolbar ────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Users size={22} color="var(--purple)" />
          <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700 }}>Users & Access Control</h2>
          <span className="badge badge-lavender">{humanUsers.length} Human Accounts</span>
        </div>

        <button
          className="btn btn-secondary"
          onClick={() => loadUsers(true)}
          disabled={loading || refreshing}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* ── Metric Cards ───────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
        <div className="card" style={{ padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Human Accounts</span>
            <Users size={18} color="var(--purple)" />
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--purple)', marginTop: '6px' }}>
            {data?.metrics?.human_users_count ?? humanUsers.length}
          </div>
        </div>

        <div className="card" style={{ padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Active Sessions</span>
            <Terminal size={18} color="#38bdf8" />
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#38bdf8', marginTop: '6px' }}>
            {data?.metrics?.active_sessions_count ?? activeSessions.length}
          </div>
        </div>

        <div className="card" style={{ padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Total SSH Keys</span>
            <Key size={18} color="var(--green)" />
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--green)', marginTop: '6px' }}>
            {data?.metrics?.total_ssh_keys ?? 0}
          </div>
        </div>

        <div className="card" style={{ padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Admin Privilege</span>
            <Shield size={18} color={data?.metrics?.is_elevated ? '#34d399' : 'var(--text-muted)'} />
          </div>
          <div
            style={{
              fontSize: '1.2rem',
              fontWeight: 700,
              color: data?.metrics?.is_elevated ? '#34d399' : 'var(--text-secondary)',
              marginTop: '10px',
            }}
          >
            {data?.metrics?.is_elevated ? 'Elevated' : 'Standard'}
          </div>
        </div>
      </div>

      {/* ── Human Users Table ──────────────────────────────────── */}
      <div className="card">
        <div className="card-header">
          <h3 style={{ margin: 0, fontSize: '1.05rem' }}>System Accounts</h3>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>UID / GID</th>
                  <th>Login Shell</th>
                  <th>Home Directory</th>
                  <th>Secondary Groups</th>
                  <th style={{ textAlign: 'right' }}>Access Control</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                      Loading system accounts…
                    </td>
                  </tr>
                ) : humanUsers.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                      No standard user accounts found.
                    </td>
                  </tr>
                ) : (
                  humanUsers.map((u) => {
                    const isSudo = u.groups?.includes('wheel') || u.groups?.includes('sudo');
                    return (
                      <tr key={u.username}>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <strong style={{ color: 'var(--text-primary)' }}>{u.username}</strong>
                            {isSudo && (
                              <span className="badge badge-lavender" style={{ fontSize: '0.7rem' }}>
                                sudo
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="font-mono" style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                          {u.uid} : {u.gid}
                        </td>
                        <td className="font-mono" style={{ fontSize: '0.82rem' }}>
                          {u.shell}
                        </td>
                        <td className="font-mono" style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                          {u.home}
                        </td>
                        <td>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', maxWidth: '240px' }}>
                            {u.groups && u.groups.length > 0 ? (
                              u.groups.map((g) => (
                                <span
                                  key={g}
                                  className="badge"
                                  style={{
                                    fontSize: '0.7rem',
                                    background: 'rgba(255,255,255,0.06)',
                                    color: 'var(--text-secondary)',
                                  }}
                                >
                                  {g}
                                </span>
                              ))
                            ) : (
                              <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>—</span>
                            )}
                          </div>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', gap: '6px' }}>
                            <button
                              className="btn btn-xs btn-secondary"
                              title="Manage SSH Keys"
                              onClick={() => handleOpenSshModal(u.username)}
                              style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                            >
                              <Key size={13} />
                              <span>SSH Keys</span>
                            </button>
                            <button
                              className="btn btn-xs btn-ghost"
                              title="Change Password"
                              onClick={() => setSelectedPassUser(u.username)}
                              style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                            >
                              <Lock size={13} />
                              <span>Password</span>
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── Active Sessions Table ──────────────────────────────── */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Terminal size={18} color="#38bdf8" />
            <h3 style={{ margin: 0, fontSize: '1.05rem' }}>Active TTY & SSH Sessions</h3>
          </div>
          <span className="badge badge-lavender">{activeSessions.length} Online</span>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Terminal (TTY)</th>
                  <th>Remote Host</th>
                  <th>Login Time</th>
                  <th>Idle Time</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {activeSessions.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
                      No active sessions reported.
                    </td>
                  </tr>
                ) : (
                  activeSessions.map((s) => (
                    <tr key={s.tty}>
                      <td>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{s.user}</span>
                      </td>
                      <td className="font-mono">{s.tty}</td>
                      <td className="font-mono" style={{ color: 'var(--text-muted)' }}>
                        {s.from || 'local'}
                      </td>
                      <td style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                        {s.login_time || '—'}
                      </td>
                      <td className="font-mono" style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                        {s.idle || '0s'}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          className="btn btn-xs btn-danger"
                          title="Terminate Session"
                          onClick={() => setPendingTerminate(s)}
                        >
                          <XCircle size={13} style={{ marginRight: '4px' }} />
                          <span>Disconnect</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── Terminate Session Modal ────────────────────────────── */}
      {pendingTerminate && (
        <ConfirmModal
          isOpen={Boolean(pendingTerminate)}
          onClose={() => setPendingTerminate(null)}
          onConfirm={handleConfirmTerminate}
          isLoading={terminateLoading}
          isDanger={true}
          title="Disconnect Session"
          message={`Are you sure you want to terminate session on ${pendingTerminate.tty} (User: ${pendingTerminate.user})?`}
          confirmLabel="Terminate Session"
        />
      )}

      {/* ── SSH Keys Modal ─────────────────────────────────────── */}
      {selectedSshUser && (
        <Modal
          isOpen={Boolean(selectedSshUser)}
          onClose={() => setSelectedSshUser(null)}
          maxWidth="640px"
          title={
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Key size={18} color="var(--purple)" /> Authorized SSH Keys: {selectedSshUser}
            </span>
          }
        >
          <div>
            <div style={{ marginBottom: '16px' }}>
              <h4 style={{ fontSize: '0.9rem', marginBottom: '8px', color: 'var(--text-secondary)' }}>
                Installed Public Keys ({sshKeys.length})
              </h4>
              {sshLoading ? (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Loading keys…</div>
              ) : sshKeys.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', padding: '12px 0' }}>
                  No SSH keys configured for this user.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '200px', overflowY: 'auto' }}>
                  {sshKeys.map((k, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        background: 'rgba(0,0,0,0.3)',
                        padding: '8px 12px',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid var(--border)',
                      }}
                    >
                      <span
                        className="font-mono"
                        style={{
                          fontSize: '0.75rem',
                          color: 'var(--text-secondary)',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          maxWidth: '480px',
                        }}
                        title={k}
                      >
                        {k}
                      </span>
                      <button
                        className="btn btn-xs btn-ghost"
                        style={{ color: '#f87171' }}
                        title="Delete Key"
                        onClick={() => handleDeleteSshKey(idx)}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <form onSubmit={handleAddSshKey} style={{ borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
              <label className="form-label" htmlFor="new-ssh-key">
                Add Public Key
              </label>
              <textarea
                id="new-ssh-key"
                className="form-input"
                rows={3}
                placeholder="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5... user@laptop"
                value={newSshKey}
                onChange={(e) => setNewSshKey(e.target.value)}
                style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.8rem', resize: 'vertical' }}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '10px' }}>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={addKeyLoading || !newSshKey.trim()}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                >
                  <Plus size={14} />
                  <span>{addKeyLoading ? 'Adding…' : 'Add Public Key'}</span>
                </button>
              </div>
            </form>
          </div>
        </Modal>
      )}

      {/* ── Change Password Modal ──────────────────────────────── */}
      {selectedPassUser && (
        <Modal
          isOpen={Boolean(selectedPassUser)}
          onClose={() => setSelectedPassUser(null)}
          title={
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Lock size={18} color="var(--purple)" /> Change Password: {selectedPassUser}
            </span>
          }
        >
          <form onSubmit={handleChangePassword}>
            <div className="form-group">
              <label className="form-label" htmlFor="new-user-password">
                New System Password
              </label>
              <input
                id="new-user-password"
                type="password"
                className="form-input"
                placeholder="Enter new password (min 4 chars)"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoFocus
                disabled={passLoading}
              />
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setSelectedPassUser(null)}
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
      )}
    </div>
  );
};
