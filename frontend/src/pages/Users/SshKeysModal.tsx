import React from 'react';
import { Modal } from '../../components/common/Modal';
import { Key, Trash2, Plus } from 'lucide-react';
import type { SshKeyItem } from '../../api/types';

const varFontMono = "'JetBrains Mono', monospace";

export interface SshKeysModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedSshUser: string;
  sshKeys: Array<SshKeyItem | string>;
  sshLoading: boolean;
  handleDeleteSshKey: (index: number) => Promise<void>;
  handleAddSshKey: (e: React.FormEvent) => Promise<void>;
  newSshKey: string;
  setNewSshKey: (key: string) => void;
  addKeyLoading: boolean;
}

export const SshKeysModal: React.FC<SshKeysModalProps> = ({
  isOpen,
  onClose,
  selectedSshUser,
  sshKeys,
  sshLoading,
  handleDeleteSshKey,
  handleAddSshKey,
  newSshKey,
  setNewSshKey,
  addKeyLoading,
}) => {
  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
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
              {sshKeys.map((item, idx) => {
                const rawKey = typeof item === 'object' && item !== null ? item.raw || item.preview : String(item);
                return (
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
                      className="font-mono ssh-modal-key-preview"
                      style={{
                        fontSize: '0.75rem',
                        color: 'var(--text-secondary)',
                      }}
                      title={rawKey}
                    >
                      {rawKey}
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
                );
              })}
            </div>
          )}
        </div>

        <form onSubmit={handleAddSshKey} style={{ borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
          <label className="form-label" htmlFor="new-ssh-key-input">
            Add Public Key
          </label>
          <textarea
            id="new-ssh-key-input"
            className="form-input"
            rows={3}
            placeholder="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5... user@laptop"
            value={newSshKey}
            onChange={(e) => setNewSshKey(e.target.value)}
            style={{ fontFamily: varFontMono, fontSize: '0.8rem', resize: 'vertical' }}
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
  );
};
