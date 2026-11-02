import React from 'react';
import { Modal } from '../../components/common/Modal';
import { Layers } from 'lucide-react';
import type { UserItem } from '../../api/types';

interface EditableGroup {
  name: string;
  label: string;
  desc: string;
  cat: 'priv' | 'hw';
}

const COMMON_GROUPS: EditableGroup[] = [
  { name: 'wheel', label: 'Admin / Wheel', desc: 'Administrative & sudo elevation privileges', cat: 'priv' },
  { name: 'sudo', label: 'Admin / Sudo', desc: 'Administrative execution privileges', cat: 'priv' },
  { name: 'docker', label: 'Docker Containers', desc: 'Control Docker containers and daemon without root', cat: 'priv' },
  { name: 'audio', label: 'Audio & Sound Card', desc: 'Audio playback, microphone, and sound card access', cat: 'hw' },
  { name: 'video', label: 'GPU & Display', desc: 'GPU acceleration, display server, and framebuffer', cat: 'hw' },
  { name: 'netdev', label: 'Network & Cellular', desc: 'Network configuration, Wi-Fi, and cellular modem', cat: 'hw' },
  { name: 'plugdev', label: 'USB OTG & Storage', desc: 'USB OTG, portable drives, and plug-and-play devices', cat: 'hw' },
  { name: 'dialout', label: 'Serial & GPS Modem', desc: 'Serial communication, modem, and GPS devices', cat: 'hw' },
  { name: 'input', label: 'Hardware Input', desc: 'Touch screen, buttons, keyboard, and pointer devices', cat: 'hw' },
  { name: 'camera', label: 'Camera Hardware', desc: 'Camera sensors and video capture (V4L2)', cat: 'hw' },
  { name: 'disk', label: 'Raw Storage Disks', desc: 'Raw disk and block storage devices', cat: 'hw' },
  { name: 'kvm', label: 'Virtualization', desc: 'Kernel-based virtual machine acceleration', cat: 'hw' },
];

function getUsername(u: UserItem): string {
  return u.name || u.username || '';
}

export interface GroupEditModalProps {
  user: UserItem | null;
  selectedGroupNames: string[];
  isOpen: boolean;
  onClose: () => void;
  onToggleGroup: (groupName: string) => void;
  onSaveGroups: () => Promise<void>;
  groupsSaving: boolean;
}

export const GroupEditModal: React.FC<GroupEditModalProps> = ({
  user,
  selectedGroupNames,
  isOpen,
  onClose,
  onToggleGroup,
  onSaveGroups,
  groupsSaving,
}) => {
  if (!isOpen || !user) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="640px"
      title={
        <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={18} color="var(--purple)" /> Edit Groups: {getUsername(user)}
        </span>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
          Select secondary groups to grant administrative or hardware subsystem privileges.
        </p>

        {/* Privileged Groups Section */}
        <div>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#c084fc', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Administrative Privileges
          </div>
          <div className="edit-groups-grid">
            {COMMON_GROUPS.filter((g) => g.cat === 'priv').map((g) => {
              const isChecked = selectedGroupNames.includes(g.name);
              return (
                <label
                  key={g.name}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                    background: isChecked ? 'rgba(168, 85, 247, 0.12)' : 'rgba(0,0,0,0.25)',
                    border: `1px solid ${isChecked ? 'rgba(168, 85, 247, 0.4)' : 'var(--border)'}`,
                    borderRadius: 'var(--radius-sm)',
                    padding: '10px',
                    cursor: 'pointer',
                    transition: 'var(--transition-fast)',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => onToggleGroup(g.name)}
                    style={{ marginTop: '2px' }}
                  />
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {g.label}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{g.desc}</div>
                  </div>
                </label>
              );
            })}
          </div>
        </div>

        {/* Hardware Groups Section */}
        <div>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#34d399', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Hardware & Subsystems
          </div>
          <div className="edit-groups-grid">
            {COMMON_GROUPS.filter((g) => g.cat === 'hw').map((g) => {
              const isChecked = selectedGroupNames.includes(g.name);
              return (
                <label
                  key={g.name}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                    background: isChecked ? 'rgba(168, 85, 247, 0.12)' : 'rgba(0,0,0,0.25)',
                    border: `1px solid ${isChecked ? 'rgba(168, 85, 247, 0.4)' : 'var(--border)'}`,
                    borderRadius: 'var(--radius-sm)',
                    padding: '10px',
                    cursor: 'pointer',
                    transition: 'var(--transition-fast)',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => onToggleGroup(g.name)}
                    style={{ marginTop: '2px' }}
                  />
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {g.label}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{g.desc}</div>
                  </div>
                </label>
              );
            })}
          </div>
        </div>

        <div className="modal-footer" style={{ borderTop: '1px solid var(--border)', paddingTop: '14px', marginTop: '4px' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
            disabled={groupsSaving}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={onSaveGroups}
            disabled={groupsSaving}
          >
            {groupsSaving ? 'Saving Groups…' : 'Save Groups'}
          </button>
        </div>
      </div>
    </Modal>
  );
};
