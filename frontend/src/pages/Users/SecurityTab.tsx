import React from 'react';
import type { UsersOverviewResponse, UserItem, SshKeyItem } from '../../api/types';
import { Shield, Lock, Key, Plus, Check, Copy, Trash2 } from 'lucide-react';

function getUsername(u: UserItem): string {
  return u.name || u.username || '';
}

export interface SecurityTabProps {
  data: UsersOverviewResponse | null;
  isElevated: boolean;
  dropElevation: () => void;
  openElevationModal: () => void;
  selectedSshUser: string;
  setSelectedSshUser: (username: string) => void;
  humanUsers: UserItem[];
  setIsSshModalOpen: (open: boolean) => void;
  sshLoading: boolean;
  sshKeys: Array<SshKeyItem | string>;
  handleCopyKey: (rawKey: string, index: number) => void;
  copiedKeyStr: string | null;
  handleDeleteSshKey: (index: number) => void;
}

export const SecurityTab: React.FC<SecurityTabProps> = ({
  data,
  isElevated,
  dropElevation,
  openElevationModal,
  selectedSshUser,
  setSelectedSshUser,
  humanUsers,
  setIsSshModalOpen,
  sshLoading,
  sshKeys,
  handleCopyKey,
  copiedKeyStr,
  handleDeleteSshKey,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Posture Summary Grid */}
      <div className="security-posture-grid">
        {/* Card 1: Privilege Elevation Engine */}
        <div
          className="security-posture-card"
          style={{ '--card-accent-color': 'var(--purple)' } as React.CSSProperties}
        >
          <div className="security-posture-title">
            <Shield size={18} color="var(--purple)" />
            <span>Privilege Elevation Engine</span>
          </div>

          <div className="security-row">
            <span className="security-row-label">Active Engine:</span>
            <span className="security-row-value" style={{ color: 'var(--accent)' }}>
              {data?.security?.elevation_engine?.toUpperCase() || 'SUDO'}
            </span>
          </div>

          <div className="security-row">
            <span className="security-row-label">Sudoers Syntax (visudo):</span>
            <span className="security-row-value">
              {data?.security?.visudo_ok ? (
                <span style={{ color: '#10b981', fontWeight: 600 }}>✓ Syntax OK</span>
              ) : (
                <span style={{ color: '#f59e0b', fontSize: '11px' }}>
                  {data?.security?.visudo_msg || 'Diagnostic restricted'}
                </span>
              )}
            </span>
          </div>

          <div className="security-row">
            <span className="security-row-label">Current Session Elevation:</span>
            <span className="security-row-value">
              {isElevated ? (
                <span style={{ color: '#10b981', fontWeight: 600 }}>Active (Root Ticket)</span>
              ) : (
                <span style={{ color: 'var(--text-muted)' }}>Not elevated</span>
              )}
            </span>
          </div>

          <div style={{ marginTop: 'auto', paddingTop: '6px' }}>
            {isElevated ? (
              <button
                className="btn btn-xs btn-secondary"
                onClick={dropElevation}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}
              >
                <Lock size={12} />
                <span>Drop Admin Elevation</span>
              </button>
            ) : (
              <button
                className="btn btn-xs btn-primary"
                onClick={() => openElevationModal()}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}
              >
                <Shield size={12} />
                <span>Elevate Session Now</span>
              </button>
            )}
          </div>
        </div>

        {/* Card 2: SSH Daemon Posture */}
        <div
          className="security-posture-card"
          style={{ '--card-accent-color': '#3b82f6' } as React.CSSProperties}
        >
          <div className="security-posture-title">
            <Lock size={18} color="#3b82f6" />
            <span>SSH Daemon Posture</span>
          </div>

          <div className="security-row">
            <span className="security-row-label">SSH Service (sshd):</span>
            <span className="security-row-value">
              {data?.security?.sshd_active ? (
                <span style={{ color: '#10b981', fontWeight: 600 }}>● Active (Listening)</span>
              ) : (
                <span style={{ color: 'var(--text-muted)' }}>Inactive / Idle</span>
              )}
            </span>
          </div>

          <div className="security-row">
            <span className="security-row-label">Root Login via SSH:</span>
            <span className="security-row-value" style={{ color: 'var(--text-secondary)' }}>
              {data?.security?.root_ssh_login || 'prohibit-password'}
            </span>
          </div>

          <div className="security-row">
            <span className="security-row-label">Password Authentication:</span>
            <span className="security-row-value" style={{ color: 'var(--text-secondary)' }}>
              {data?.security?.password_auth || 'yes'}
            </span>
          </div>
        </div>
      </div>

      {/* SSH Authorized Keys Hub */}
      <div className="card">
        <div
          className="card-header"
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}
        >
          <div>
            <h3 style={{ margin: 0, fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Key size={16} color="var(--purple)" />
              <span>SSH Authorized Keys Hub</span>
            </h3>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Manage public keys in ~/.ssh/authorized_keys for remote terminal access
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <label htmlFor="ssh-user-select" style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Manage Keys for:
              </label>
              <select
                id="ssh-user-select"
                className="input"
                value={selectedSshUser}
                onChange={(e) => setSelectedSshUser(e.target.value)}
                style={{ fontSize: '12px', padding: '4px 10px', height: '32px' }}
              >
                {humanUsers.map((u) => {
                  const uname = getUsername(u);
                  return (
                    <option key={uname} value={uname}>
                      {uname} ({u.ssh_keys_count ?? 0} keys)
                    </option>
                  );
                })}
              </select>
            </div>

            <button
              className="btn btn-primary btn-sm"
              onClick={() => setIsSshModalOpen(true)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              <Plus size={14} />
              <span>Add SSH Key</span>
            </button>
          </div>
        </div>

        <div className="card-body">
          {sshLoading ? (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
              Loading authorized keys…
            </div>
          ) : sshKeys.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '36px 20px', color: 'var(--text-muted)' }}>
              <p style={{ marginBottom: '14px', fontSize: '13.5px' }}>
                No authorized SSH keys installed for <strong>{selectedSshUser}</strong>.
              </p>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => setIsSshModalOpen(true)}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                <Plus size={14} />
                <span>Add First Public Key</span>
              </button>
            </div>
          ) : (
            <div>
              {sshKeys.map((item, idx) => {
                const isObj = typeof item === 'object' && item !== null;
                const keyType = isObj ? (item as SshKeyItem).type : 'SSH Key';
                const keyComment = isObj
                  ? (item as SshKeyItem).comment || 'Public Key'
                  : typeof item === 'string'
                  ? item.split(' ').slice(2).join(' ') || item.slice(0, 32)
                  : 'Key';
                const keyPreview = isObj
                  ? (item as SshKeyItem).preview
                  : typeof item === 'string'
                  ? item.slice(0, 48) + '…'
                  : '';
                const rawKey = isObj ? (item as SshKeyItem).raw || (item as SshKeyItem).preview : String(item);
                const keyIndex = isObj ? (item as SshKeyItem).index ?? idx : idx;

                return (
                  <div key={idx} className="ssh-key-row">
                    <div className="ssh-key-info">
                      <div className="ssh-key-header-line">
                        <span className="ssh-key-type">{keyType}</span>
                        <span className="ssh-key-comment">{keyComment}</span>
                      </div>
                      <div className="ssh-key-fingerprint">{keyPreview || rawKey}</div>
                    </div>

                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                      <button
                        className="btn btn-xs btn-ghost"
                        onClick={() => handleCopyKey(rawKey, idx)}
                        title="Copy public key to clipboard"
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                      >
                        {copiedKeyStr === String(idx) ? <Check size={13} color="#10b981" /> : <Copy size={13} />}
                        <span>{copiedKeyStr === String(idx) ? 'Copied' : 'Copy'}</span>
                      </button>

                      <button
                        className="btn btn-xs btn-danger"
                        onClick={() => handleDeleteSshKey(keyIndex)}
                        title="Remove this public key"
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                      >
                        <Trash2 size={13} />
                        <span>Remove</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
