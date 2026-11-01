import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../api/client';
import {
  UsersOverviewResponse,
  UserItem,
  UserSessionItem,
  GroupCategoryItem,
  LoginHistoryItem,
  SshKeyItem,
} from '../../api/types';
import { useToast } from '../../context/ToastContext';
import { useAuth } from '../../context/AuthContext';
import { useClipboard } from '../../hooks/useClipboard';
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
  Copy,
  Check,
  Search,
  ChevronDown,
  ChevronUp,
  Cpu,
  Layers,
  ExternalLink,
  Clock,
} from 'lucide-react';

type TabType = 'accounts' | 'sessions' | 'groups' | 'security';
type GroupFilterType = 'all' | 'Privileged' | 'Hardware' | 'Services' | 'System';

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

export const UsersPage: React.FC = () => {
  const { addToast } = useToast();
  const { session, isElevated, openElevationModal, dropElevation } = useAuth();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<TabType>('accounts');
  const [data, setData] = useState<UsersOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // System Accounts collapsible drawer & search
  const [isSystemUsersOpen, setIsSystemUsersOpen] = useState(false);
  const [systemSearch, setSystemSearch] = useState('');

  // Groups & Hardware filters
  const [groupFilter, setGroupFilter] = useState<GroupFilterType>('all');
  const [groupSearch, setGroupSearch] = useState('');

  // Terminate session state
  const [pendingTerminate, setPendingTerminate] = useState<UserSessionItem | null>(null);
  const [terminateLoading, setTerminateLoading] = useState(false);

  // SSH Keys Modal & Hub state
  const [selectedSshUser, setSelectedSshUser] = useState<string>('');
  const [sshKeys, setSshKeys] = useState<Array<SshKeyItem | string>>([]);
  const [sshLoading, setSshLoading] = useState(false);
  const [isSshModalOpen, setIsSshModalOpen] = useState(false);
  const [newSshKey, setNewSshKey] = useState('');
  const [addKeyLoading, setAddKeyLoading] = useState(false);
  const { copiedKey: copiedKeyStr, copy: copyToClipboard } = useClipboard();

  // Edit Groups Modal state
  const [selectedEditUser, setSelectedEditUser] = useState<UserItem | null>(null);
  const [selectedGroupNames, setSelectedGroupNames] = useState<string[]>([]);
  const [groupsSaving, setGroupsSaving] = useState(false);

  // Password Modal state
  const [selectedPassUser, setSelectedPassUser] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passLoading, setPassLoading] = useState(false);

  // Load all user data
  const loadUsers = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const res = await api.get<UsersOverviewResponse>('/api/users');
      setData(res);

      // Default selected SSH user if not set
      setSelectedSshUser((prev) => {
        if (!prev && res.human_users && res.human_users.length > 0) {
          return getUsername(res.human_users[0]);
        }
        return prev;
      });
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

  // Load SSH keys when selected user changes
  const loadUserSshKeys = useCallback(async (username: string) => {
    if (!username) return;
    setSshLoading(true);
    try {
      const res = await api.get<{ username: string; keys: Array<SshKeyItem | string> }>(
        `/api/users/${encodeURIComponent(username)}/ssh-keys`
      );
      setSshKeys(res.keys || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : `Failed to load SSH keys for ${username}`;
      addToast(msg, 'error');
      setSshKeys([]);
    } finally {
      setSshLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    if (selectedSshUser) {
      loadUserSshKeys(selectedSshUser);
    }
  }, [selectedSshUser, loadUserSshKeys]);

  // Normalized datasets
  const humanUsers: UserItem[] = useMemo(() => data?.human_users || [], [data]);
  const systemUsers: UserItem[] = useMemo(() => data?.system_users || [], [data]);
  const activeSessions: UserSessionItem[] = useMemo(() => data?.active_sessions || [], [data]);
  const loginHistory: LoginHistoryItem[] = useMemo(() => data?.login_history || [], [data]);

  // Normalize groups_categorized
  const categorizedGroups: GroupCategoryItem[] = useMemo(() => {
    if (!data?.groups_categorized) return [];
    if (Array.isArray(data.groups_categorized)) {
      return data.groups_categorized as GroupCategoryItem[];
    }
    // Backward-compatibility dictionary format
    const record = data.groups_categorized as Record<string, string[]>;
    const items: GroupCategoryItem[] = [];
    Object.entries(record).forEach(([category, groupList]) => {
      (groupList || []).forEach((gName, idx) => {
        items.push({
          name: gName,
          gid: 1000 + idx,
          members: [],
          category,
          description: `Group ${gName}`,
          member_count: 0,
        });
      });
    });
    return items;
  }, [data]);

  // Filtered system accounts
  const filteredSystemUsers = useMemo(() => {
    const q = systemSearch.toLowerCase().trim();
    if (!q) return systemUsers;
    return systemUsers.filter((u) => {
      const uname = getUsername(u).toLowerCase();
      const shell = (u.shell || '').toLowerCase();
      const uidStr = String(u.uid);
      const homeStr = (u.home || '').toLowerCase();
      return uname.includes(q) || shell.includes(q) || uidStr.includes(q) || homeStr.includes(q);
    });
  }, [systemUsers, systemSearch]);

  // Filtered groups
  const filteredGroups = useMemo(() => {
    let result = categorizedGroups;
    if (groupFilter !== 'all') {
      if (groupFilter === 'System') {
        result = result.filter((g) => g.category === 'System' || g.category === 'General');
      } else {
        result = result.filter((g) => g.category === groupFilter);
      }
    }
    const q = groupSearch.toLowerCase().trim();
    if (q) {
      result = result.filter((g) => {
        const nameMatch = g.name.toLowerCase().includes(q);
        const descMatch = (g.description || '').toLowerCase().includes(q);
        const memberMatch = (g.members || []).some((m) => m.toLowerCase().includes(q));
        return nameMatch || descMatch || memberMatch;
      });
    }
    return result;
  }, [categorizedGroups, groupFilter, groupSearch]);

  // Group counts by category
  const groupCounts = useMemo(() => {
    let priv = 0;
    let hw = 0;
    let serv = 0;
    let sys = 0;
    categorizedGroups.forEach((g) => {
      if (g.category === 'Privileged') priv++;
      else if (g.category === 'Hardware') hw++;
      else if (g.category === 'Services') serv++;
      else sys++;
    });
    return { all: categorizedGroups.length, priv, hw, serv, sys };
  }, [categorizedGroups]);

  // Top metric values
  const primaryHumanUser = humanUsers[0];
  const totalSshKeys = data?.metrics?.total_ssh_keys ?? humanUsers.reduce((acc, u) => acc + (u.ssh_keys_count || 0), 0);
  const elevationEngine = data?.security?.elevation_engine || 'sudo';
  const sshdActive = data?.security?.sshd_active ?? true;

  // Active user names
  const activeUserSet = useMemo(() => {
    return new Set(activeSessions.map((s) => s.user));
  }, [activeSessions]);

  // ── Actions ──────────────────────────────────────────────────────────

  // Terminate active terminal session
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

  // Open SSH Modal for a specific user
  const handleOpenSshModal = async (username: string) => {
    setSelectedSshUser(username);
    setIsSshModalOpen(true);
    setNewSshKey('');
    await loadUserSshKeys(username);
  };

  // Add SSH Key
  const handleAddSshKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSshUser || !newSshKey.trim()) return;
    setAddKeyLoading(true);
    try {
      const res = await api.post<{ success: boolean; message?: string }>(
        `/api/users/${encodeURIComponent(selectedSshUser)}/ssh-keys`,
        { key: newSshKey.trim() }
      );
      if (res.success) {
        addToast('SSH key added successfully', 'success');
        setNewSshKey('');
        await loadUserSshKeys(selectedSshUser);
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
        await loadUserSshKeys(selectedSshUser);
        await loadUsers(true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to remove SSH key';
      addToast(msg, 'error');
    }
  };

  // Copy public key to clipboard
  const handleCopyKey = (keyText: string, index: number) => {
    copyToClipboard(keyText, String(index));
    addToast('Public key copied to clipboard', 'info');
  };

  // Open Edit Groups Modal
  const handleOpenEditGroups = (user: UserItem) => {
    setSelectedEditUser(user);
    setSelectedGroupNames([...(user.groups || [])]);
  };

  // Toggle group selection
  const handleToggleGroup = (groupName: string) => {
    setSelectedGroupNames((prev) =>
      prev.includes(groupName) ? prev.filter((g) => g !== groupName) : [...prev, groupName]
    );
  };

  // Save edited groups
  const handleSaveGroups = async () => {
    if (!selectedEditUser) return;
    const username = getUsername(selectedEditUser);
    setGroupsSaving(true);
    try {
      const res = await api.post<{ success: boolean; message?: string }>(
        `/api/users/${encodeURIComponent(username)}/groups`,
        { groups: selectedGroupNames }
      );
      if (res.success) {
        addToast(res.message || `Updated groups for ${username}`, 'success');
        setSelectedEditUser(null);
        await loadUsers(true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update groups';
      addToast(msg, 'error');
    } finally {
      setGroupsSaving(false);
    }
  };

  // Change Password
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPassUser) return;
    if (newPassword.length < 4) {
      addToast('Password must be at least 4 characters long', 'error');
      return;
    }
    if (confirmPassword && newPassword !== confirmPassword) {
      addToast('Passwords do not match', 'error');
      return;
    }

    setPassLoading(true);
    try {
      const res = await api.post<{ success: boolean; message?: string }>(
        `/api/users/${encodeURIComponent(selectedPassUser)}/password`,
        { new_password: newPassword }
      );
      if (res.success) {
        addToast(`Password successfully updated for ${selectedPassUser}`, 'success');
        setSelectedPassUser(null);
        setNewPassword('');
        setConfirmPassword('');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update password';
      addToast(msg, 'error');
    } finally {
      setPassLoading(false);
    }
  };

  return (
    <div className="users-page">
      {/* ── Top Header Strip ────────────────────────────────────── */}
      <div className="users-header-strip">
        <div className="users-header-title">
          <h2>
            <Users size={22} color="var(--purple)" />
            <span>Identity & Access Control</span>
          </h2>
          <p>Manage user accounts, active terminal sessions, hardware privileges, and SSH authorized keys</p>
        </div>

        <div className="users-header-actions">
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => loadUsers(true)}
            disabled={loading || refreshing}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            title="Refresh all user data"
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* ── Top 4 Summary Metric Cards ─────────────────────────── */}
      <div className="users-metrics-grid">
        {/* Metric 1: Active Logins */}
        <div
          className="users-metric-card"
          style={
            {
              '--card-accent-color': '#10b981',
              '--icon-bg': 'rgba(16, 185, 129, 0.15)',
              '--icon-color': '#10b981',
            } as React.CSSProperties
          }
        >
          <div className="users-metric-icon">
            <Terminal size={22} />
          </div>
          <div className="users-metric-info">
            <div className="users-metric-label">Active Logins</div>
            <div className="users-metric-value">{activeSessions.length} Active</div>
            <div className="users-metric-sub">
              {activeSessions.length > 0
                ? `${activeSessions[0].user} on ${activeSessions[0].tty} (${activeSessions[0].from || activeSessions[0].host || 'local'})`
                : 'No terminal sessions connected'}
            </div>
          </div>
        </div>

        {/* Metric 2: Human Accounts */}
        <div
          className="users-metric-card"
          style={
            {
              '--card-accent-color': 'var(--accent)',
              '--icon-bg': 'var(--accent-dim)',
              '--icon-color': 'var(--accent)',
            } as React.CSSProperties
          }
        >
          <div className="users-metric-icon">
            <Users size={22} />
          </div>
          <div className="users-metric-info">
            <div className="users-metric-label">Human Accounts</div>
            <div className="users-metric-value">
              {humanUsers.length} Account{humanUsers.length === 1 ? '' : 's'}
            </div>
            <div className="users-metric-sub">
              {primaryHumanUser?.home_storage
                ? `Home: ${primaryHumanUser.home_storage.used_gb} GB used (${primaryHumanUser.home_storage.percent_used}%)`
                : `${systemUsers.length} system daemons`}
            </div>
          </div>
        </div>

        {/* Metric 3: Privilege Posture */}
        <div
          className="users-metric-card"
          style={
            {
              '--card-accent-color': 'var(--purple)',
              '--icon-bg': 'var(--purple-dim)',
              '--icon-color': 'var(--purple)',
            } as React.CSSProperties
          }
        >
          <div className="users-metric-icon">
            <Shield size={22} />
          </div>
          <div className="users-metric-info">
            <div className="users-metric-label">Privilege Posture</div>
            <div className="users-metric-value">
              {isElevated ? 'Admin Active' : `${elevationEngine.toUpperCase()} Ready`}
            </div>
            <div className="users-metric-sub">
              {isElevated ? 'Elevation ticket verified' : 'Standard user session'}
            </div>
          </div>
        </div>

        {/* Metric 4: SSH Access */}
        <div
          className="users-metric-card"
          style={
            {
              '--card-accent-color': '#3b82f6',
              '--icon-bg': 'rgba(59, 130, 246, 0.15)',
              '--icon-color': '#3b82f6',
            } as React.CSSProperties
          }
        >
          <div className="users-metric-icon">
            <Key size={22} />
          </div>
          <div className="users-metric-info">
            <div className="users-metric-label">SSH Access</div>
            <div className="users-metric-value">
              {totalSshKeys} Key{totalSshKeys === 1 ? '' : 's'}
            </div>
            <div className="users-metric-sub">
              {sshdActive ? 'sshd daemon active' : 'sshd installed'}
            </div>
          </div>
        </div>
      </div>

      {/* ── Navigation Tabs ─────────────────────────────────────── */}
      <div className="tabs">
        <button
          className={`tab ${activeTab === 'accounts' ? 'active' : ''}`}
          onClick={() => setActiveTab('accounts')}
        >
          <Users size={15} />
          <span>Accounts & Users</span>
        </button>

        <button
          className={`tab ${activeTab === 'sessions' ? 'active' : ''}`}
          onClick={() => setActiveTab('sessions')}
        >
          <Terminal size={15} />
          <span>Active Sessions</span>
          <span className="badge badge-lavender" style={{ fontSize: '10px', padding: '1px 6px' }}>
            {activeSessions.length}
          </span>
        </button>

        <button
          className={`tab ${activeTab === 'groups' ? 'active' : ''}`}
          onClick={() => setActiveTab('groups')}
        >
          <Layers size={15} />
          <span>Groups & Hardware</span>
        </button>

        <button
          className={`tab ${activeTab === 'security' ? 'active' : ''}`}
          onClick={() => setActiveTab('security')}
        >
          <Shield size={15} />
          <span>Security & SSH Keys</span>
        </button>
      </div>

      {/* ══════════════════════════════════════════════════════════════
          TAB 1: ACCOUNTS & USERS
         ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'accounts' && (
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
                const isCurrent = u.is_current || session?.username === uname;
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
      )}

      {/* ══════════════════════════════════════════════════════════════
          TAB 2: ACTIVE SESSIONS & RECENT LOGINS
         ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'sessions' && (
        <div className="users-sessions-container">
          {/* Active Terminal & Remote Logins */}
          <div className="card users-sessions-card">
            <div className="card-header sessions-card-header">
              <div className="sessions-header-titles">
                <h3 className="sessions-card-title">Active Terminal & Remote Logins</h3>
                <span className="sessions-card-subtitle">
                  Real-time logged-in TTYs & SSH sessions
                </span>
              </div>
              <span className="badge badge-lavender sessions-online-badge">{activeSessions.length} Online</span>
            </div>

            <div className="card-body sessions-card-body" style={{ padding: 0 }}>
              <div className="sessions-table-wrap">
                <table className="table sessions-table active-sessions-table">
                  <thead>
                    <tr>
                      <th className="col-status" style={{ width: '40px' }}>Status</th>
                      <th className="col-user">User</th>
                      <th className="col-tty">Terminal (TTY)</th>
                      <th className="col-host">Remote Host / IP</th>
                      <th className="col-login">Login Time</th>
                      <th className="col-idle">Idle Duration</th>
                      <th className="col-actions" style={{ textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeSessions.length === 0 ? (
                      <tr className="sessions-empty-row">
                        <td colSpan={7} className="sessions-empty-cell">
                          <div className="sessions-empty-content">
                            <Terminal size={22} className="sessions-empty-icon" />
                            <span>No active terminal or SSH sessions connected</span>
                          </div>
                        </td>
                      </tr>
                    ) : (
                      activeSessions.map((s) => (
                        <tr key={s.tty} className="session-item-row">
                          <td className="session-cell-status">
                            <span className="session-beacon" title="Session Active" />
                          </td>
                          <td className="session-cell-user">
                            <div className="session-user-wrap">
                              <strong className="session-username">{s.user}</strong>
                            </div>
                          </td>
                          <td className="session-cell-tty font-mono">
                            <span className="session-tty-badge">{s.tty}</span>
                          </td>
                          <td className="session-cell-host font-mono">
                            <span className="sessions-meta-label">Host: </span>
                            <span className="sessions-meta-val">{s.from || s.host || 'local'}</span>
                          </td>
                          <td className="session-cell-login">
                            <span className="sessions-meta-label">Login: </span>
                            <span className="sessions-meta-val">{s.login_time || '—'}</span>
                          </td>
                          <td className="session-cell-idle font-mono">
                            <span className="sessions-meta-label">Idle: </span>
                            <span className="sessions-meta-val">{s.idle || '0s'}</span>
                          </td>
                          <td className="session-cell-actions">
                            <button
                              className="btn btn-xs btn-danger session-disconnect-btn"
                              onClick={() => setPendingTerminate(s)}
                              title={`Terminate session on ${s.tty}`}
                            >
                              <XCircle size={13} />
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

          {/* Recent Login History (lastlog/wtmp) */}
          <div className="card users-sessions-card">
            <div className="card-header sessions-card-header">
              <div className="sessions-header-titles">
                <h3 className="sessions-card-title">Recent Login History</h3>
                <span className="sessions-card-subtitle">
                  Last 10 system authentication sessions (from lastlog/wtmp)
                </span>
              </div>
            </div>

            <div className="card-body sessions-card-body" style={{ padding: 0 }}>
              <div className="sessions-table-wrap">
                <table className="table sessions-table history-sessions-table">
                  <thead>
                    <tr>
                      <th className="hist-col-user">User</th>
                      <th className="hist-col-tty">Terminal</th>
                      <th className="hist-col-host">Host</th>
                      <th className="hist-col-time">Time / Session Duration</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loginHistory.length === 0 ? (
                      <tr className="sessions-empty-row">
                        <td colSpan={4} className="sessions-empty-cell">
                          <div className="sessions-empty-content">
                            <Clock size={20} className="sessions-empty-icon" />
                            <span>No recent logins recorded</span>
                          </div>
                        </td>
                      </tr>
                    ) : (
                      loginHistory.map((h, idx) => (
                        <tr key={idx} className="history-item-row">
                          <td className="hist-cell-user font-mono">
                            <span className="hist-username">{h.user}</span>
                          </td>
                          <td className="hist-cell-tty font-mono">
                            <span className="hist-tty-badge">{h.tty}</span>
                          </td>
                          <td className="hist-cell-host font-mono">
                            <span className="hist-host-badge">{h.host || 'local'}</span>
                          </td>
                          <td className="hist-cell-time">
                            <span className="hist-time-val">{h.time}</span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════
          TAB 3: GROUPS & HARDWARE
         ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'groups' && (
        <div className="groups-tab-container">
          {/* Filter Pills Bar & Search Toolbar */}
          <div className="groups-toolbar">
            <div className="filter-pills-bar">
              <button
                className={`filter-pill ${groupFilter === 'all' ? 'active' : ''}`}
                onClick={() => setGroupFilter('all')}
              >
                All Groups ({groupCounts.all})
              </button>
              <button
                className={`filter-pill ${groupFilter === 'Privileged' ? 'active' : ''}`}
                onClick={() => setGroupFilter('Privileged')}
              >
                Privileged ({groupCounts.priv})
              </button>
              <button
                className={`filter-pill ${groupFilter === 'Hardware' ? 'active' : ''}`}
                onClick={() => setGroupFilter('Hardware')}
              >
                Phone & Hardware ({groupCounts.hw})
              </button>
              <button
                className={`filter-pill ${groupFilter === 'Services' ? 'active' : ''}`}
                onClick={() => setGroupFilter('Services')}
              >
                Services ({groupCounts.serv})
              </button>
              <button
                className={`filter-pill ${groupFilter === 'System' ? 'active' : ''}`}
                onClick={() => setGroupFilter('System')}
              >
                System ({groupCounts.sys})
              </button>
            </div>

            <div className="groups-search-wrap">
              <Search
                size={14}
                className="groups-search-icon"
              />
              <input
                type="search"
                className="input groups-search-input"
                placeholder="Search groups (e.g. wheel, audio, docker)..."
                value={groupSearch}
                onChange={(e) => setGroupSearch(e.target.value)}
              />
            </div>
          </div>

          {/* Groups Table Card */}
          <div className="card groups-card">
            <div className="card-body groups-card-body">
              <div className="groups-table-wrap">
                <table className="table groups-table">
                  <thead>
                    <tr>
                      <th className="col-group-name">Group Name</th>
                      <th className="col-group-gid">GID</th>
                      <th className="col-group-cat">Category</th>
                      <th className="col-group-desc">Subsystem / Permission</th>
                      <th className="col-group-members">Members</th>
                      <th className="col-group-actions">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredGroups.length === 0 ? (
                      <tr className="groups-empty-row">
                        <td colSpan={6} className="groups-empty-cell">
                          <div className="groups-empty-content">
                            <Layers size={18} className="groups-empty-icon" />
                            <span>No groups match current filter</span>
                          </div>
                        </td>
                      </tr>
                    ) : (
                      filteredGroups.map((g) => {
                        let catBadge = <span className="badge badge-neutral">System</span>;
                        if (g.category === 'Privileged') {
                          catBadge = <span className="badge badge-lavender">Privileged</span>;
                        } else if (g.category === 'Hardware') {
                          catBadge = <span className="badge badge-success">Hardware</span>;
                        } else if (g.category === 'Services') {
                          catBadge = <span className="badge badge-services">Services</span>;
                        }

                        return (
                          <tr key={g.name} className="group-item-row">
                            <td className="group-cell-name font-mono">
                              <span className="group-name-text">{g.name}</span>
                            </td>
                            <td className="group-cell-gid font-mono">
                              <span className="group-gid-badge">
                                <span className="group-gid-prefix">GID </span>
                                {g.gid}
                              </span>
                            </td>
                            <td className="group-cell-cat">{catBadge}</td>
                            <td className="group-cell-desc">
                              <span className="group-meta-label">Subsystem / Permission</span>
                              <span className="group-desc-text">{g.description}</span>
                            </td>
                            <td className="group-cell-members">
                              <span className="group-meta-label">Members</span>
                              <div className="group-members-wrap">
                                {g.members && g.members.length > 0 ? (
                                  g.members.map((m) => {
                                    const isHuman = humanUsers.some((u) => getUsername(u) === m);
                                    return (
                                      <span
                                        key={m}
                                        className={`group-tag ${isHuman ? 'tag-wheel' : ''}`}
                                      >
                                        {m}
                                      </span>
                                    );
                                  })
                                ) : (
                                  <span className="group-no-members">—</span>
                                )}
                              </div>
                            </td>
                            <td className="group-cell-actions">
                              {primaryHumanUser && (
                                <button
                                  className="btn btn-xs btn-ghost group-action-btn"
                                  onClick={() => handleOpenEditGroups(primaryHumanUser)}
                                  title={`Edit group assignments for ${getUsername(primaryHumanUser)}`}
                                >
                                  <span>Edit</span>
                                </button>
                              )}
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
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════
          TAB 4: SECURITY & SSH KEYS
         ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'security' && (
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
      )}

      {/* ══════════════════════════════════════════════════════════════
          MODALS
         ══════════════════════════════════════════════════════════════ */}

      {/* ── Disconnect Session Modal ─────────────────────────────── */}
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

      {/* ── Add / Manage SSH Keys Modal ──────────────────────────── */}
      {isSshModalOpen && (
        <Modal
          isOpen={isSshModalOpen}
          onClose={() => setIsSshModalOpen(false)}
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
      )}

      {/* ── Edit Groups Modal ────────────────────────────────────── */}
      {selectedEditUser && (
        <Modal
          isOpen={Boolean(selectedEditUser)}
          onClose={() => setSelectedEditUser(null)}
          maxWidth="640px"
          title={
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Layers size={18} color="var(--purple)" /> Edit Groups: {getUsername(selectedEditUser)}
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
                        onChange={() => handleToggleGroup(g.name)}
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
                        background: isChecked ? 'rgba(16, 185, 129, 0.12)' : 'rgba(0,0,0,0.25)',
                        border: `1px solid ${isChecked ? 'rgba(16, 185, 129, 0.4)' : 'var(--border)'}`,
                        borderRadius: 'var(--radius-sm)',
                        padding: '10px',
                        cursor: 'pointer',
                        transition: 'var(--transition-fast)',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => handleToggleGroup(g.name)}
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
                onClick={() => setSelectedEditUser(null)}
                disabled={groupsSaving}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleSaveGroups}
                disabled={groupsSaving}
              >
                {groupsSaving ? 'Saving Groups…' : 'Save Groups'}
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* ── Change Password Modal ────────────────────────────────── */}
      {selectedPassUser && (
        <Modal
          isOpen={Boolean(selectedPassUser)}
          onClose={() => {
            setSelectedPassUser(null);
            setNewPassword('');
            setConfirmPassword('');
          }}
          title={
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Lock size={18} color="var(--purple)" /> Change Password: {selectedPassUser}
            </span>
          }
        >
          <form onSubmit={handleChangePassword}>
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
                onClick={() => {
                  setSelectedPassUser(null);
                  setNewPassword('');
                  setConfirmPassword('');
                }}
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

const varFontMono = "'JetBrains Mono', monospace";
