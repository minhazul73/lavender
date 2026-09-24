import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../../api/client';
import { PackagesOverviewResponse, PackageItem } from '../../api/types';
import { useToast } from '../../context/ToastContext';
import { ConfirmModal } from '../../components/common/ConfirmModal';
import {
  Package,
  Search,
  RefreshCw,
  ArrowUpCircle,
  Download,
  Trash2,
  CheckCircle2,
  Layers,
  Sparkles,
} from 'lucide-react';

export const PackagesPage: React.FC = () => {
  const { addToast } = useToast();
  const [data, setData] = useState<PackagesOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Tab: 'upgradable' | 'installed' | 'search'
  const [activeTab, setActiveTab] = useState<'upgradable' | 'installed' | 'search'>('upgradable');

  // Search in repos
  const [searchQuery, setSearchQuery] = useState('');
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchResults, setSearchResults] = useState<PackageItem[]>([]);

  // Filter in installed list
  const [installedFilter, setInstalledFilter] = useState('');

  // Package Action modal (install, upgrade, remove)
  const [pendingAction, setPendingAction] = useState<{
    type: 'upgrade' | 'install' | 'remove' | 'upgrade-all';
    package?: string;
  } | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const loadPackages = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const res = await api.get<PackagesOverviewResponse>('/api/packages');
      setData(res);
      // Auto-switch to installed tab if no upgradable packages
      if (res.upgradable_count === 0 && !isRefresh) {
        setActiveTab('installed');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch packages';
      addToast(msg, 'error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [addToast]);

  useEffect(() => {
    loadPackages();
  }, [loadPackages]);

  // Execute Search in repos
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearchLoading(true);
    setActiveTab('search');
    try {
      const res = await api.get<{ results: PackageItem[] }>(
        `/api/packages/search?query=${encodeURIComponent(searchQuery.trim())}`
      );
      setSearchResults(res.results || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Search failed';
      addToast(msg, 'error');
    } finally {
      setSearchLoading(false);
    }
  };

  // Execute Install, Upgrade, or Remove
  const handleExecuteAction = async () => {
    if (!pendingAction) return;
    setActionLoading(true);
    try {
      if (pendingAction.type === 'upgrade-all') {
        const res = await api.post<{ success: boolean; output?: string }>('/api/packages/upgrade');
        if (res.success) {
          addToast('System packages successfully upgraded', 'success');
          setPendingAction(null);
          await loadPackages(true);
        }
      } else if (pendingAction.type === 'upgrade' && pendingAction.package) {
        const res = await api.post<{ success: boolean; output?: string }>(
          `/api/packages/upgrade?package=${encodeURIComponent(pendingAction.package)}`
        );
        if (res.success) {
          addToast(`Package ${pendingAction.package} upgraded`, 'success');
          setPendingAction(null);
          await loadPackages(true);
        }
      } else if (pendingAction.type === 'install' && pendingAction.package) {
        const res = await api.post<{ success: boolean; output?: string }>(
          `/api/packages/install?package=${encodeURIComponent(pendingAction.package)}`
        );
        if (res.success) {
          addToast(`Package ${pendingAction.package} installed`, 'success');
          setPendingAction(null);
          await loadPackages(true);
        }
      } else if (pendingAction.type === 'remove' && pendingAction.package) {
        const res = await api.post<{ success: boolean; output?: string }>(
          `/api/packages/remove?package=${encodeURIComponent(pendingAction.package)}`
        );
        if (res.success) {
          addToast(`Package ${pendingAction.package} removed`, 'success');
          setPendingAction(null);
          await loadPackages(true);
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Package operation failed';
      addToast(msg, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // Filter installed packages
  const filteredInstalled = useMemo(() => {
    if (!data?.installed) return [];
    if (!installedFilter.trim()) return data.installed.slice(0, 100);
    const q = installedFilter.toLowerCase();
    return data.installed
      .filter((p) => p.name.toLowerCase().includes(q) || (p.description || '').toLowerCase().includes(q))
      .slice(0, 100);
  }, [data?.installed, installedFilter]);

  const upgradableList = data?.upgradable || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* ── Header & Distro Summary ────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Package size={22} color="var(--purple)" />
          <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700 }}>Package Manager</h2>
          <span className="badge badge-lavender font-mono">{data?.backend_name || 'Detecting…'}</span>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          {upgradableList.length > 0 && (
            <button
              className="btn btn-primary"
              onClick={() => setPendingAction({ type: 'upgrade-all' })}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              <ArrowUpCircle size={15} />
              <span>Upgrade All ({upgradableList.length})</span>
            </button>
          )}

          <button
            className="btn btn-secondary"
            onClick={() => loadPackages(true)}
            disabled={loading || refreshing}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* ── Summary Counters ───────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        <div
          className={`card ${activeTab === 'upgradable' ? 'active-glow' : ''}`}
          style={{ padding: '16px', cursor: 'pointer' }}
          onClick={() => setActiveTab('upgradable')}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Upgrades Available</span>
            <ArrowUpCircle size={18} color={upgradableList.length > 0 ? '#38bdf8' : 'var(--text-muted)'} />
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#38bdf8', marginTop: '6px' }}>
            {data?.upgradable_count ?? 0}
          </div>
        </div>

        <div
          className={`card ${activeTab === 'installed' ? 'active-glow' : ''}`}
          style={{ padding: '16px', cursor: 'pointer' }}
          onClick={() => setActiveTab('installed')}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Installed Packages</span>
            <Layers size={18} color="var(--purple)" />
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--purple)', marginTop: '6px' }}>
            {data?.installed_count ?? 0}
          </div>
        </div>

        <div
          className={`card ${activeTab === 'search' ? 'active-glow' : ''}`}
          style={{ padding: '16px', cursor: 'pointer' }}
          onClick={() => setActiveTab('search')}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Search Repositories</span>
            <Sparkles size={18} color="var(--green)" />
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--green)', marginTop: '6px' }}>
            {searchResults.length}
          </div>
        </div>
      </div>

      {/* ── Search Bar ─────────────────────────────────────────── */}
      <form onSubmit={handleSearch} style={{ display: 'flex', gap: '8px' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Search
            size={16}
            style={{
              position: 'absolute',
              left: '12px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--text-muted)',
            }}
          />
          <input
            type="search"
            className="form-input"
            placeholder="Search online repositories (e.g. htop, curl, nodejs)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ paddingLeft: '36px' }}
          />
        </div>
        <button type="submit" className="btn btn-primary" disabled={searchLoading}>
          {searchLoading ? 'Searching…' : 'Search Repos'}
        </button>
      </form>

      {/* ── Main Tab Content ───────────────────────────────────── */}
      <div className="card">
        {/* Tab Header */}
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: '16px' }}>
            <button
              className={`btn btn-ghost ${activeTab === 'upgradable' ? 'btn-active' : ''}`}
              onClick={() => setActiveTab('upgradable')}
              style={{ fontWeight: activeTab === 'upgradable' ? 700 : 500 }}
            >
              Upgradable ({upgradableList.length})
            </button>
            <button
              className={`btn btn-ghost ${activeTab === 'installed' ? 'btn-active' : ''}`}
              onClick={() => setActiveTab('installed')}
              style={{ fontWeight: activeTab === 'installed' ? 700 : 500 }}
            >
              Installed ({data?.installed_count ?? 0})
            </button>
            <button
              className={`btn btn-ghost ${activeTab === 'search' ? 'btn-active' : ''}`}
              onClick={() => setActiveTab('search')}
              style={{ fontWeight: activeTab === 'search' ? 700 : 500 }}
            >
              Repository Search ({searchResults.length})
            </button>
          </div>

          {activeTab === 'installed' && (
            <input
              type="text"
              className="form-input"
              placeholder="Filter installed..."
              value={installedFilter}
              onChange={(e) => setInstalledFilter(e.target.value)}
              style={{ width: '200px', padding: '4px 10px', fontSize: '0.82rem' }}
            />
          )}
        </div>

        {/* Tab Body */}
        <div className="card-body" style={{ padding: 0 }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Package Name</th>
                  <th>Current Version</th>
                  <th>Target Version</th>
                  <th>Description</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {activeTab === 'upgradable' ? (
                  upgradableList.length === 0 ? (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                        <CheckCircle2 size={24} color="#34d399" style={{ marginBottom: '8px' }} />
                        <div>System is completely up to date. No pending updates found.</div>
                      </td>
                    </tr>
                  ) : (
                    upgradableList.map((p) => (
                      <tr key={p.name}>
                        <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{p.name}</td>
                        <td className="font-mono" style={{ color: 'var(--text-muted)' }}>
                          {p.version || '—'}
                        </td>
                        <td className="font-mono" style={{ color: '#38bdf8', fontWeight: 600 }}>
                          {p.new_version || 'Available'}
                        </td>
                        <td style={{ color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
                          {p.description || '—'}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <button
                            className="btn btn-xs btn-primary"
                            onClick={() => setPendingAction({ type: 'upgrade', package: p.name })}
                          >
                            <ArrowUpCircle size={13} style={{ marginRight: '4px' }} />
                            <span>Upgrade</span>
                          </button>
                        </td>
                      </tr>
                    ))
                  )
                ) : activeTab === 'installed' ? (
                  filteredInstalled.length === 0 ? (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                        No installed packages matching query.
                      </td>
                    </tr>
                  ) : (
                    filteredInstalled.map((p) => (
                      <tr key={p.name}>
                        <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{p.name}</td>
                        <td className="font-mono">{p.version || 'installed'}</td>
                        <td className="font-mono" style={{ color: 'var(--text-muted)' }}>
                          —
                        </td>
                        <td style={{ color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
                          {p.description || '—'}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <button
                            className="btn btn-xs btn-ghost"
                            style={{ color: '#f87171' }}
                            title="Remove Package"
                            onClick={() => setPendingAction({ type: 'remove', package: p.name })}
                          >
                            <Trash2 size={13} />
                          </button>
                        </td>
                      </tr>
                    ))
                  )
                ) : (
                  searchResults.length === 0 ? (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                        Search packages from online repositories above.
                      </td>
                    </tr>
                  ) : (
                    searchResults.map((p) => (
                      <tr key={p.name}>
                        <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{p.name}</td>
                        <td className="font-mono" style={{ color: 'var(--text-muted)' }}>
                          {p.installed ? p.version || 'installed' : 'Not installed'}
                        </td>
                        <td className="font-mono" style={{ color: 'var(--green)' }}>
                          {p.new_version || p.version || 'Available'}
                        </td>
                        <td style={{ color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
                          {p.description || '—'}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <button
                            className="btn btn-xs btn-primary"
                            onClick={() => setPendingAction({ type: 'install', package: p.name })}
                          >
                            <Download size={13} style={{ marginRight: '4px' }} />
                            <span>Install</span>
                          </button>
                        </td>
                      </tr>
                    ))
                  )
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── Action Confirmation Modal ──────────────────────────── */}
      {pendingAction && (
        <ConfirmModal
          isOpen={Boolean(pendingAction)}
          onClose={() => setPendingAction(null)}
          onConfirm={handleExecuteAction}
          isLoading={actionLoading}
          isDanger={pendingAction.type === 'remove'}
          title={`${pendingAction.type.toUpperCase()} Package`}
          message={
            pendingAction.type === 'upgrade-all'
              ? 'Are you sure you want to upgrade all pending system packages? This will require administrative privileges.'
              : `Are you sure you want to execute '${pendingAction.type}' on package '${pendingAction.package}'?`
          }
          confirmLabel={
            pendingAction.type === 'upgrade-all'
              ? 'Upgrade All'
              : pendingAction.type.charAt(0).toUpperCase() + pendingAction.type.slice(1)
          }
        />
      )}
    </div>
  );
};
