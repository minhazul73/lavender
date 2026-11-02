import React, { useState, useEffect, useCallback, useMemo } from 'react';
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
import { ConfirmModal } from '../../components/common/ConfirmModal';
import { SshKeysModal } from './SshKeysModal';
import { GroupEditModal } from './GroupEditModal';
import { PasswordModal } from './PasswordModal';
import { AccountsTab } from './AccountsTab';
import { SessionsTab } from './SessionsTab';
import { GroupsTab, GroupFilterType } from './GroupsTab';
import { SecurityTab } from './SecurityTab';
import {
  Users,
  Shield,
  Key,
  Terminal,
  RefreshCw,
  Layers,
} from 'lucide-react';

type TabType = 'accounts' | 'sessions' | 'groups' | 'security';

function getUsername(u: UserItem): string {
  return u.name || u.username || '';
}

export const UsersPage: React.FC = () => {
  const { addToast } = useToast();
  const { session, isElevated, openElevationModal, dropElevation } = useAuth();

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
        <AccountsTab
          humanUsers={humanUsers}
          systemUsers={systemUsers}
          filteredSystemUsers={filteredSystemUsers}
          loading={loading}
          activeUserSet={activeUserSet}
          currentUsername={session?.username}
          isSystemUsersOpen={isSystemUsersOpen}
          setIsSystemUsersOpen={setIsSystemUsersOpen}
          systemSearch={systemSearch}
          setSystemSearch={setSystemSearch}
          handleOpenSshModal={handleOpenSshModal}
          handleOpenEditGroups={handleOpenEditGroups}
          setSelectedPassUser={setSelectedPassUser}
        />
      )}

      {/* ══════════════════════════════════════════════════════════════
          TAB 2: ACTIVE SESSIONS & RECENT LOGINS
         ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'sessions' && (
        <SessionsTab
          activeSessions={activeSessions}
          loginHistory={loginHistory}
          onTerminateSession={(s) => setPendingTerminate(s)}
        />
      )}

      {/* ══════════════════════════════════════════════════════════════
          TAB 3: GROUPS & HARDWARE
         ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'groups' && (
        <GroupsTab
          groupFilter={groupFilter}
          setGroupFilter={setGroupFilter}
          groupCounts={groupCounts}
          groupSearch={groupSearch}
          setGroupSearch={setGroupSearch}
          filteredGroups={filteredGroups}
          humanUsers={humanUsers}
          primaryHumanUser={primaryHumanUser}
          handleOpenEditGroups={handleOpenEditGroups}
        />
      )}

      {/* ══════════════════════════════════════════════════════════════
          TAB 4: SECURITY & SSH KEYS
         ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'security' && (
        <SecurityTab
          data={data}
          isElevated={isElevated}
          dropElevation={dropElevation}
          openElevationModal={openElevationModal}
          selectedSshUser={selectedSshUser}
          setSelectedSshUser={setSelectedSshUser}
          humanUsers={humanUsers}
          setIsSshModalOpen={setIsSshModalOpen}
          sshLoading={sshLoading}
          sshKeys={sshKeys}
          handleCopyKey={handleCopyKey}
          copiedKeyStr={copiedKeyStr}
          handleDeleteSshKey={handleDeleteSshKey}
        />
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
      <SshKeysModal
        isOpen={isSshModalOpen}
        onClose={() => setIsSshModalOpen(false)}
        selectedSshUser={selectedSshUser}
        sshKeys={sshKeys}
        sshLoading={sshLoading}
        handleDeleteSshKey={handleDeleteSshKey}
        handleAddSshKey={handleAddSshKey}
        newSshKey={newSshKey}
        setNewSshKey={setNewSshKey}
        addKeyLoading={addKeyLoading}
      />

      {/* ── Edit Groups Modal ────────────────────────────────────── */}
      <GroupEditModal
        user={selectedEditUser}
        selectedGroupNames={selectedGroupNames}
        isOpen={Boolean(selectedEditUser)}
        onClose={() => setSelectedEditUser(null)}
        onToggleGroup={handleToggleGroup}
        onSaveGroups={handleSaveGroups}
        groupsSaving={groupsSaving}
      />

      {/* ── Change Password Modal ────────────────────────────────── */}
      <PasswordModal
        selectedPassUser={selectedPassUser}
        isOpen={Boolean(selectedPassUser)}
        onClose={() => {
          setSelectedPassUser(null);
          setNewPassword('');
          setConfirmPassword('');
        }}
        onSubmit={handleChangePassword}
        newPassword={newPassword}
        setNewPassword={setNewPassword}
        confirmPassword={confirmPassword}
        setConfirmPassword={setConfirmPassword}
        passLoading={passLoading}
      />
    </div>
  );
};
