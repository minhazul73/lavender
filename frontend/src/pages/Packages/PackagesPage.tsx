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
      const reqOptions = { timeoutMs: 600_000 };
      if (pendingAction.type === 'upgrade-all') {
        const res = await api.post<{ success: boolean; output?: string }>('/api/packages/upgrade', undefined, reqOptions);
        if (res.success) {
          addToast('System packages successfully upgraded', 'success');
          setPendingAction(null);
          await loadPackages(true);
        }
      } else if (pendingAction.type === 'upgrade' && pendingAction.package) {
        const res = await api.post<{ success: boolean; output?: string }>(
          `/api/packages/upgrade?package=${encodeURIComponent(pendingAction.package)}`,
          undefined,
          reqOptions
        );
        if (res.success) {
          addToast(`Package ${pendingAction.package} upgraded`, 'success');
          setPendingAction(null);
          await loadPackages(true);
        }
      } else if (pendingAction.type === 'install' && pendingAction.package) {
        const res = await api.post<{ success: boolean; output?: string }>(
          `/api/packages/install?package=${encodeURIComponent(pendingAction.package)}`,
          undefined,
          reqOptions
        );
        if (res.success) {
          addToast(`Package ${pendingAction.package} installed`, 'success');
          setPendingAction(null);
          await loadPackages(true);
        }
      } else if (pendingAction.type === 'remove' && pendingAction.package) {
        const res = await api.post<{ success: boolean; output?: string }>(
          `/api/packages/remove?package=${encodeURIComponent(pendingAction.package)}`,
          undefined,
          reqOptions
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
    <div className="packages-page">
      {/* ── Header & Distro Summary ────────────────────────────── */}
      <div className="packages-header-strip">
        <div className="packages-header-title-group">
          <div className="packages-title-row">
            <Package size={22} color="var(--purple)" className="packages-title-icon" />
            <h2 className="packages-page-title">Package Manager</h2>
          </div>
          <span className="badge badge-lavender packages-backend-badge font-mono">
            {data?.backend_name || 'Detecting…'}
          </span>
        </div>

        <div className="packages-header-actions">
          {upgradableList.length > 0 && (
            <button
              className="btn btn-primary packages-upgrade-all-btn"
              onClick={() => setPendingAction({ type: 'upgrade-all' })}
            >
              <ArrowUpCircle size={15} />
              <span>Upgrade All ({upgradableList.length})</span>
            </button>
          )}

          <button
            className="btn btn-secondary packages-refresh-btn"
            onClick={() => loadPackages(true)}
            disabled={loading || refreshing}
            title="Refresh package lists"
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* ── Summary Counters ───────────────────────────────────── */}
      <div className="packages-metrics-grid">
        <div
          className={`card packages-metric-card ${activeTab === 'upgradable' ? 'active-glow' : ''}`}
          onClick={() => setActiveTab('upgradable')}
        >
          <div className="packages-metric-header">
            <span className="packages-metric-label">
              <span className="label-full">Upgrades Available</span>
              <span className="label-short">Upgrades</span>
            </span>
            <ArrowUpCircle size={16} color={upgradableList.length > 0 ? '#38bdf8' : 'var(--text-muted)'} />
          </div>
          <div className="packages-metric-value val-upgrades">
            {data?.upgradable_count ?? 0}
          </div>
        </div>

        <div
          className={`card packages-metric-card ${activeTab === 'installed' ? 'active-glow' : ''}`}
          onClick={() => setActiveTab('installed')}
        >
          <div className="packages-metric-header">
            <span className="packages-metric-label">
              <span className="label-full">Installed Packages</span>
              <span className="label-short">Installed</span>
            </span>
            <Layers size={16} color="var(--purple)" />
          </div>
          <div className="packages-metric-value val-installed">
            {data?.installed_count ?? 0}
          </div>
        </div>

        <div
          className={`card packages-metric-card ${activeTab === 'search' ? 'active-glow' : ''}`}
          onClick={() => setActiveTab('search')}
        >
          <div className="packages-metric-header">
            <span className="packages-metric-label">
              <span className="label-full">Search Repositories</span>
              <span className="label-short">Search</span>
            </span>
            <Sparkles size={16} color="var(--green)" />
          </div>
          <div className="packages-metric-value val-search">
            {searchResults.length}
          </div>
        </div>
      </div>

      {/* ── Search Bar ─────────────────────────────────────────── */}
      <form onSubmit={handleSearch} className="packages-search-form">
        <div className="packages-search-input-wrap">
          <Search size={16} className="packages-search-icon" />
          <input
            type="search"
            className="form-input packages-search-input"
            placeholder="Search online repositories (e.g. htop, curl)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <button type="submit" className="btn btn-primary packages-search-btn" disabled={searchLoading}>
          <Search size={14} />
          <span>{searchLoading ? 'Searching…' : 'Search Repos'}</span>
        </button>
      </form>

      {/* ── Main Tab Content ───────────────────────────────────── */}
      <div className="card packages-main-card">
        {/* Tab Header */}
        <div className="card-header packages-tab-header">
          <div className="packages-tabs-list">
            <button
              className={`packages-tab-btn ${activeTab === 'upgradable' ? 'active' : ''}`}
              onClick={() => setActiveTab('upgradable')}
            >
              Upgradable ({upgradableList.length})
            </button>
            <button
              className={`packages-tab-btn ${activeTab === 'installed' ? 'active' : ''}`}
              onClick={() => setActiveTab('installed')}
            >
              Installed ({data?.installed_count ?? 0})
            </button>
            <button
              className={`packages-tab-btn ${activeTab === 'search' ? 'active' : ''}`}
              onClick={() => setActiveTab('search')}
            >
              Repository Search ({searchResults.length})
            </button>
          </div>

          {activeTab === 'installed' && (
            <div className="packages-filter-wrap">
              <Search size={13} className="packages-filter-icon" />
              <input
                type="text"
                className="form-input packages-filter-input"
                placeholder="Filter installed..."
                value={installedFilter}
                onChange={(e) => setInstalledFilter(e.target.value)}
              />
            </div>
          )}
        </div>

        {/* Tab Body */}
        <div className="card-body packages-card-body" style={{ padding: 0 }}>
          <div className="packages-table-wrap">
            <table className="table packages-table">
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
                    <tr className="pkg-empty-row">
                      <td colSpan={5} className="pkg-empty-state">
                        <CheckCircle2 size={24} color="#34d399" style={{ marginBottom: '8px' }} />
                        <div>System is completely up to date. No pending updates found.</div>
                      </td>
                    </tr>
                  ) : (
                    upgradableList.map((p) => (
                      <tr key={p.name} className="pkg-row pkg-row-upgradable">
                        <td className="pkg-cell-name">
                          <Package size={14} className="pkg-name-icon" />
                          <span className="pkg-name-text">{p.name}</span>
                        </td>
                        <td className="pkg-cell-current font-mono">
                          <span className="pkg-ver-label">Current:</span>
                          <span className="pkg-ver-cur-val">{p.version || '—'}</span>
                        </td>
                        <td className="pkg-cell-target font-mono">
                          <span className="pkg-ver-label">Target:</span>
                          <span className="pkg-ver-target-val">{p.new_version || 'Available'}</span>
                        </td>
                        <td className={`pkg-cell-desc ${!p.description ? 'pkg-desc-empty' : ''}`}>
                          {p.description || '—'}
                        </td>
                        <td className="pkg-cell-actions">
                          <button
                            className="btn btn-xs btn-primary pkg-action-btn"
                            onClick={() => setPendingAction({ type: 'upgrade', package: p.name })}
                          >
                            <ArrowUpCircle size={13} />
                            <span>Upgrade</span>
                          </button>
                        </td>
                      </tr>
                    ))
                  )
                ) : activeTab === 'installed' ? (
                  filteredInstalled.length === 0 ? (
                    <tr className="pkg-empty-row">
                      <td colSpan={5} className="pkg-empty-state">
                        No installed packages matching query.
                      </td>
                    </tr>
                  ) : (
                    filteredInstalled.map((p) => (
                      <tr key={p.name} className="pkg-row pkg-row-installed">
                        <td className="pkg-cell-name">
                          <Package size={14} className="pkg-name-icon" />
                          <span className="pkg-name-text">{p.name}</span>
                        </td>
                        <td className="pkg-cell-current font-mono">
                          <span className="pkg-ver-label">Installed:</span>
                          <span className="pkg-ver-cur-val">{p.version || 'installed'}</span>
                        </td>
                        <td className="pkg-cell-target font-mono">
                          <span className="pkg-target-dash">—</span>
                        </td>
                        <td className={`pkg-cell-desc ${!p.description ? 'pkg-desc-empty' : ''}`}>
                          {p.description || '—'}
                        </td>
                        <td className="pkg-cell-actions">
                          <button
                            className="btn btn-xs btn-ghost pkg-remove-btn"
                            title="Remove Package"
                            onClick={() => setPendingAction({ type: 'remove', package: p.name })}
                          >
                            <Trash2 size={13} />
                            <span className="pkg-remove-label">Remove</span>
                          </button>
                        </td>
                      </tr>
                    ))
                  )
                ) : (
                  searchResults.length === 0 ? (
                    <tr className="pkg-empty-row">
                      <td colSpan={5} className="pkg-empty-state">
                        Search packages from online repositories above.
                      </td>
                    </tr>
                  ) : (
                    searchResults.map((p) => (
                      <tr key={p.name} className="pkg-row pkg-row-search">
                        <td className="pkg-cell-name">
                          <Package size={14} className="pkg-name-icon" />
                          <span className="pkg-name-text">{p.name}</span>
                        </td>
                        <td className="pkg-cell-current font-mono">
                          <span className="pkg-ver-label">Status:</span>
                          <span className="pkg-ver-cur-val">{p.installed ? p.version || 'installed' : 'Not installed'}</span>
                        </td>
                        <td className="pkg-cell-target font-mono">
                          <span className="pkg-ver-label">Available:</span>
                          <span className="pkg-ver-target-val pkg-avail-val">{p.new_version || p.version || 'Available'}</span>
                        </td>
                        <td className={`pkg-cell-desc ${!p.description ? 'pkg-desc-empty' : ''}`}>
                          {p.description || '—'}
                        </td>
                        <td className="pkg-cell-actions">
                          <button
                            className="btn btn-xs btn-primary pkg-action-btn"
                            onClick={() => setPendingAction({ type: 'install', package: p.name })}
                          >
                            <Download size={13} />
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
