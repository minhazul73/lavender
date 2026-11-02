import React from 'react';
import { useNavigate } from 'react-router-dom';
import type { UserItem } from '../../api/types';
import {
  Key,
  Layers,
  Lock,
  ExternalLink,
  Cpu,
  ChevronDown,
  ChevronUp,
  Search,
} from 'lucide-react';

function getUsername(u: UserItem): string {
  return u.name || u.username || '';
}

export interface AccountsTabProps {
  humanUsers: UserItem[];
  systemUsers: UserItem[];
  filteredSystemUsers: UserItem[];
  loading: boolean;
  activeUserSet: Set<string>;
  currentUsername?: string;
  isSystemUsersOpen: boolean;
  setIsSystemUsersOpen: React.Dispatch<React.SetStateAction<boolean>>;
  systemSearch: string;
  setSystemSearch: React.Dispatch<React.SetStateAction<string>>;
  handleOpenSshModal: (username: string) => void;
  handleOpenEditGroups: (user: UserItem) => void;
  setSelectedPassUser: (username: string) => void;
}

export const AccountsTab: React.FC<AccountsTabProps> = ({
  humanUsers,
  systemUsers,
  filteredSystemUsers,
  loading,
  activeUserSet,
  currentUsername,
  isSystemUsersOpen,
  setIsSystemUsersOpen,
  systemSearch,
  setSystemSearch,
  handleOpenSshModal,
  handleOpenEditGroups,
  setSelectedPassUser,
}) => {
  const navigate = useNavigate();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Interactive Human Users Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
        <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>Interactive Human Users</span>
          <span className="badge badge-lavender" style={{ fontSize: '11px', padding: '2px 8px' }}>
            {humanUsers.length}
          </span>
        </h3>
      </div>

      {/* User Cards Grid */}
      {loading ? (
        <div className="card" style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
          Loading user accounts…
        </div>
      ) : humanUsers.length === 0 ? (
        <div className="card" style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
          No interactive human users detected in /etc/passwd.
        </div>
      ) : (
        <div className="user-cards-grid">
          {humanUsers.map((u) => {
            const uname = getUsername(u);
            const initial = (uname[0] || 'U').toUpperCase();
            const isCurrent = u.is_current || currentUsername === uname;
            const isAdmin = u.is_admin || u.groups?.includes('wheel') || u.groups?.includes('sudo');
            const isOnline = u.is_active || activeUserSet.has(uname);
            const storage = u.home_storage;

            return (
              <div key={uname} className={`user-card ${isCurrent ? 'is-current-user' : ''}`}>
                {/* Card Header */}
                <div className="user-card-header">
                  <div className={`user-avatar-lg ${isOnline ? 'user-online' : ''}`}>
                    {initial}
                  </div>

                  <div className="user-title-wrap">
                    <div className="user-name-title">
                      <span>{uname}</span>
                      {isCurrent && (
                        <span className="badge badge-success" style={{ fontSize: '10px', padding: '1px 6px' }}>
                          YOU
                        </span>
                      )}
                      {isAdmin && (
                        <span className="badge badge-lavender" style={{ fontSize: '10px', padding: '1px 6px' }}>
                          ADMIN / WHEEL
                        </span>
                      )}
                    </div>
                    <div className="user-subtitle">
                      UID: {u.uid} | GID: {u.gid}
                    </div>
                  </div>
                </div>

                {/* Card Body Details */}
                <div className="user-card-body">
                  <div className="user-info-row">
                    <span className="user-info-label">Home:</span>
                    <span className="user-info-val" title={u.home}>
                      {u.home}
                    </span>
                  </div>

                  <div className="user-info-row">
                    <span className="user-info-label">Shell:</span>
                    <span className="user-info-val">{u.shell}</span>
                  </div>

                  <div className="user-info-row">
                    <span className="user-info-label">SSH Keys:</span>
                    <span className="user-info-val" style={{ color: 'var(--accent)' }}>
                      {u.ssh_keys_count ?? 0} key installed
                    </span>
                  </div>

                  {/* Home Disk Usage Progress */}
                  {storage && (
                    <div className="user-storage-container">
                      <div className="user-storage-header">
                        <span className="user-storage-title">Disk Usage ({u.home})</span>
                        <span className="user-storage-stats">
                          <strong>{storage.used_gb} GB</strong> / {storage.total_gb} GB ({storage.percent_used}%)
                        </span>
                      </div>
                      <div className="user-storage-track">
                        <div
                          className={`user-storage-fill ${
                            storage.percent_used > 90
                              ? 'danger'
                              : storage.percent_used > 75
                              ? 'warn'
                              : ''
                          }`}
                          style={{ width: `${Math.min(storage.percent_used, 100)}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Group Memberships */}
                  <div>
                    <div className="user-info-label" style={{ marginBottom: '6px' }}>
                      Group Memberships:
                    </div>
                    <div className="user-groups-tag-container">
                      {u.groups && u.groups.length > 0 ? (
                        u.groups.map((g) => {
                          let tagClass = '';
                          if (g === 'wheel' || g === 'sudo') tagClass = 'tag-wheel';
                          else if (g === 'docker') tagClass = 'tag-docker';
                          else if (['audio', 'video', 'netdev', 'plugdev', 'dialout', 'input', 'camera', 'disk', 'kvm'].includes(g)) {
                            tagClass = 'tag-hardware';
                          } else {
                            tagClass = 'tag-services';
                          }
                          return (
                            <span key={g} className={`group-tag ${tagClass}`}>
                              {g}
                            </span>
                          );
                        })
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Primary group only</span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Card Actions */}
                <div className="user-card-actions">
                  <button
                    className="btn btn-xs btn-secondary"
                    onClick={() => handleOpenSshModal(uname)}
                    title="Manage authorized SSH keys"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}
                  >
                    <Key size={12} />
                    <span>SSH Keys ({u.ssh_keys_count ?? 0})</span>
                  </button>

                  <button
                    className="btn btn-xs btn-secondary"
                    onClick={() => handleOpenEditGroups(u)}
                    title="Edit secondary group memberships"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}
                  >
                    <Layers size={12} />
                    <span>Edit Groups</span>
                  </button>

                  <button
                    className="btn btn-xs btn-secondary"
                    onClick={() => setSelectedPassUser(uname)}
                    title="Change login password"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}
                  >
                    <Lock size={12} />
                    <span>Password</span>
                  </button>

                  <button
                    className="btn btn-xs btn-ghost user-action-btn-processes"
                    onClick={() => navigate(`/processes?user=${encodeURIComponent(uname)}`)}
                    title="View user running processes"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                  >
                    <span>Processes</span>
                    <ExternalLink size={12} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Collapsible System & Service Accounts Drawer */}
      <div className="card system-accounts-card" style={{ marginTop: '10px' }}>
        <div
          className="card-header system-accounts-toggle"
          onClick={() => setIsSystemUsersOpen(!isSystemUsersOpen)}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
            <Cpu size={16} color="var(--text-secondary)" style={{ flexShrink: 0 }} />
            <h3 style={{ margin: 0, fontSize: '0.92rem', whiteSpace: 'nowrap' }}>
              <span className="system-accounts-title-desktop">System & Service Accounts</span>
              <span className="system-accounts-title-mobile">System Accounts</span>
            </h3>
            <span className="badge badge-neutral" style={{ fontSize: '11px', flexShrink: 0 }}>
              {systemUsers.length}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)', flexShrink: 0 }}>
            <span style={{ fontSize: '12px' }}>{isSystemUsersOpen ? 'Collapse' : 'Expand'}</span>
            {isSystemUsersOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>
        </div>

        {isSystemUsersOpen && (
          <div className="card-body" style={{ paddingTop: '8px' }}>
            <div className="system-accounts-filter-bar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '14px' }}>
              <div className="system-accounts-search-wrap" style={{ position: 'relative', width: '100%', maxWidth: '340px' }}>
                <Search
                  size={15}
                  style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}
                />
                <input
                  type="search"
                  className="input"
                  placeholder="Search system accounts (e.g. root, daemon, caddy)..."
                  value={systemSearch}
                  onChange={(e) => setSystemSearch(e.target.value)}
                  style={{ width: '100%', paddingLeft: '32px' }}
                />
              </div>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                Showing {filteredSystemUsers.length} of {systemUsers.length} accounts
              </span>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>UID</th>
                    <th>GID</th>
                    <th>Home</th>
                    <th>Shell</th>
                    <th>Groups</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSystemUsers.length === 0 ? (
                    <tr>
                      <td colSpan={6} style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
                        No system accounts match filter
                      </td>
                    </tr>
                  ) : (
                    filteredSystemUsers.map((u) => {
                      const uname = getUsername(u);
                      return (
                        <tr key={uname}>
                          <td className="font-mono" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                            {uname}
                          </td>
                          <td className="font-mono" style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                            {u.uid}
                          </td>
                          <td className="font-mono" style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                            {u.gid}
                          </td>
                          <td className="font-mono" style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                            {u.home}
                          </td>
                          <td className="font-mono" style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                            {u.shell}
                          </td>
                          <td>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', maxWidth: '240px' }}>
                              {(u.groups || []).slice(0, 3).map((g) => (
                                <span key={g} className="group-tag" style={{ fontSize: '10px' }}>
                                  {g}
                                </span>
                              ))}
                              {(u.groups || []).length > 3 && (
                                <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                                  +{u.groups.length - 3}
                                </span>
                              )}
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
        )}
      </div>
    </div>
  );
};
