import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { api } from '../../api/client';
import { ProcessItem, ProcessesOverviewResponse } from '../../api/types';
import { useToast } from '../../context/ToastContext';
import { ConfirmModal } from '../../components/common/ConfirmModal';
import { CustomSelect, SelectOption } from '../../components/common/CustomSelect';
import { Activity, Search, RefreshCw, Layers, Clock } from 'lucide-react';
import { ProcessTable } from './ProcessTable';

export const ProcessesPage: React.FC = () => {
  const { addToast } = useToast();
  const [data, setData] = useState<ProcessesOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);

  // Filters & Controls
  const [search, setSearch] = useState('');
  const [userFilter, setUserFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'mem' | 'cpu' | 'pid' | 'name' | 'user'>('mem');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [pageSize, setPageSize] = useState<number | 'all'>(50);
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Expandable row state & copy feedback
  const [expandedPid, setExpandedPid] = useState<number | null>(null);
  const [copiedType, setCopiedType] = useState<string | null>(null);

  // Kill process state
  const [pendingKill, setPendingKill] = useState<ProcessItem | null>(null);
  const [killLoading, setKillLoading] = useState(false);

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard?.writeText(text);
    setCopiedType(key);
    addToast(key.startsWith('cmd') ? 'Command copied to clipboard' : 'PID copied to clipboard', 'success');
    setTimeout(() => setCopiedType(null), 1500);
  };

  const loadProcesses = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      // Use limit=0 to retrieve all processes for client-side search & filtering
      const res = await api.get<ProcessesOverviewResponse>(
        `/api/system/processes?sort_by=${sortBy}&limit=0`
      );
      setData(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load processes';
      addToast(msg, 'error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [sortBy, addToast]);

  useEffect(() => {
    loadProcesses();
  }, [loadProcesses]);

  useEffect(() => {
    if (!autoRefresh) return;
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') {
        loadProcesses(true);
      }
    }, 5000);
    return () => clearInterval(timer);
  }, [autoRefresh, loadProcesses]);

  // Counts per user for the user dropdown
  const userCounts = useMemo(() => {
    if (!data?.processes) return {};
    const counts: Record<string, number> = {};
    for (const p of data.processes) {
      const u = p.user || 'unknown';
      counts[u] = (counts[u] || 0) + 1;
    }
    return counts;
  }, [data?.processes]);

  const uniqueUsers = useMemo(() => Object.keys(userCounts).sort(), [userCounts]);

  const userOptions = useMemo<SelectOption[]>(() => {
    const list: SelectOption[] = [{ value: 'all', label: `All Users (${data?.processes?.length || 0})` }];
    for (const u of uniqueUsers) {
      list.push({ value: u, label: u, count: userCounts[u] });
    }
    return list;
  }, [uniqueUsers, userCounts, data?.processes?.length]);

  const sortOptions = useMemo(() => [
    { value: 'mem', label: 'Memory (Highest)' },
    { value: 'cpu', label: 'CPU (Highest)' },
    { value: 'pid', label: 'PID (Ascending)' },
    { value: 'name', label: 'Name (A–Z)' },
  ], []);

  const showOptions = useMemo(() => [
    { value: 25, label: '25' },
    { value: 50, label: '50' },
    { value: 100, label: '100' },
    { value: 'all', label: 'All' },
  ], []);

  // Filter & sort processes
  const filteredProcesses = useMemo(() => {
    if (!data?.processes) return [];
    const q = search.trim().toLowerCase();

    return data.processes
      .filter((p) => {
        if (userFilter !== 'all' && p.user !== userFilter) return false;
        if (!q) return true;
        return (
          p.name?.toLowerCase().includes(q) ||
          p.command.toLowerCase().includes(q) ||
          p.user.toLowerCase().includes(q) ||
          String(p.pid).includes(q)
        );
      })
      .sort((a, b) => {
        let cmp = 0;
        if (sortBy === 'pid') cmp = (a.pid || 0) - (b.pid || 0);
        else if (sortBy === 'user') cmp = (a.user || '').localeCompare(b.user || '');
        else if (sortBy === 'cpu') cmp = (a.cpu || a.cpu_time || 0) - (b.cpu || b.cpu_time || 0);
        else if (sortBy === 'name') cmp = (a.name || a.command || '').toLowerCase().localeCompare((b.name || b.command || '').toLowerCase());
        else cmp = (a.mem || 0) - (b.mem || 0);
        return sortOrder === 'asc' ? cmp : -cmp;
      });
  }, [data?.processes, search, userFilter, sortBy, sortOrder]);

  const effectivePageSize = pageSize === 'all' ? Infinity : pageSize;
  const totalPages =
    effectivePageSize === Infinity ? 1 : Math.max(1, Math.ceil(filteredProcesses.length / effectivePageSize));

  const paginatedProcesses = useMemo(() => {
    if (effectivePageSize === Infinity) return filteredProcesses;
    const start = (currentPage - 1) * effectivePageSize;
    return filteredProcesses.slice(start, start + effectivePageSize);
  }, [filteredProcesses, currentPage, effectivePageSize]);

  // Handle Sort Change from column header click
  const handleSort = (field: 'mem' | 'cpu' | 'pid' | 'name' | 'user') => {
    if (sortBy === field) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(field);
      setSortOrder(field === 'pid' || field === 'name' || field === 'user' ? 'asc' : 'desc');
    }
    setCurrentPage(1);
  };

  // Handle Sort Change from dropdown
  const handleSortDropdown = (field: 'mem' | 'cpu' | 'pid' | 'name') => {
    setSortBy(field);
    setSortOrder(field === 'pid' || field === 'name' ? 'asc' : 'desc');
    setCurrentPage(1);
  };

  // Kill Process
  const handleConfirmKill = async () => {
    if (!pendingKill) return;
    setKillLoading(true);
    try {
      const res = await api.post<{ success: boolean; output?: string }>(
        `/api/system/processes/kill?pid=${pendingKill.pid}`
      );
      if (res.success) {
        addToast(`Process ${pendingKill.name || pendingKill.pid} (PID ${pendingKill.pid}) terminated`, 'success');
        setPendingKill(null);
        await loadProcesses(true);
      } else {
        addToast(res.output || `Failed to kill PID ${pendingKill.pid}`, 'error');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : `Failed to kill process`;
      addToast(msg, 'error');
    } finally {
      setKillLoading(false);
    }
  };

  const loadInfo = data?.load;
  const parsedMem = data?.memory?.parsed;
  const memPercent = parsedMem?.percent ?? 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* ── System Resource Summary Cards ─────────────────────── */}
      <div className="info-grid">
        {/* Load Average Card */}
        <div className="info-card">
          <div className="info-card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div className="info-card-icon load"><Activity size={18} /></div>
              <div>
                <div className="info-card-title">System Load</div>
                <div className="info-card-subtitle">Load Average (1m, 5m, 15m)</div>
              </div>
            </div>
          </div>
          <div>
            <div className="load-values">
              <div className="load-pill">
                <span className="load-num">
                  {loadInfo?.['1min'] != null || loadInfo?.['1m'] != null || loadInfo?.load1 != null
                    ? Number(loadInfo?.['1min'] ?? loadInfo?.['1m'] ?? loadInfo?.load1).toFixed(2) : '—'}
                </span>
                <span className="load-tag">1 min</span>
              </div>
              <div className="load-pill">
                <span className="load-num">
                  {loadInfo?.['5min'] != null || loadInfo?.['5m'] != null || loadInfo?.load5 != null
                    ? Number(loadInfo?.['5min'] ?? loadInfo?.['5m'] ?? loadInfo?.load5).toFixed(2) : '—'}
                </span>
                <span className="load-tag">5 min</span>
              </div>
              <div className="load-pill">
                <span className="load-num">
                  {loadInfo?.['15min'] != null || loadInfo?.['15m'] != null || loadInfo?.load15 != null
                    ? Number(loadInfo?.['15min'] ?? loadInfo?.['15m'] ?? loadInfo?.load15).toFixed(2) : '—'}
                </span>
                <span className="load-tag">15 min</span>
              </div>
            </div>
            <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '6px' }}>
              Tasks: <strong style={{ color: 'var(--text-primary)' }}>{loadInfo?.running ?? '—'}</strong> running of{' '}
              <strong style={{ color: 'var(--text-primary)' }}>{loadInfo?.total ?? data?.processes?.length ?? '—'}</strong> total
            </div>
          </div>
        </div>

        {/* Memory Usage Card */}
        <div className="info-card">
          <div className="info-card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div className="info-card-icon memory"><Layers size={18} /></div>
              <div>
                <div className="info-card-title">Memory Usage</div>
                <div className="info-card-subtitle">
                  {parsedMem?.used && parsedMem?.total ? `${parsedMem.used} of ${parsedMem.total} utilized` : 'RAM & Swap Status'}
                </div>
              </div>
            </div>
            <span className="badge user" style={{ fontSize: '11px', textTransform: 'none' }}>
              {memPercent ? `${memPercent.toFixed(1)}%` : '—'}
            </span>
          </div>
          <div>
            <div className="proc-bar-outer">
              <div
                className={`proc-bar-inner ${memPercent > 85 ? 'crit' : memPercent > 70 ? 'warn' : ''}`}
                style={{ width: `${Math.min(100, Math.max(0, memPercent || 0))}%` }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>
                Used: <strong style={{ color: 'var(--text-primary)' }}>{parsedMem?.used || '—'}</strong>
              </span>
              <span style={{ color: 'var(--text-muted)' }}>Free: {parsedMem?.free || '—'}</span>
              <span style={{ color: 'var(--text-muted)' }}>
                Swap: {parsedMem?.swap_used ? `${parsedMem.swap_used} / ${parsedMem.swap_total || '0'}` : parsedMem?.swap_total || '0'}
              </span>
            </div>
          </div>
        </div>

        {/* System Uptime Card */}
        <div className="info-card">
          <div className="info-card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div className="info-card-icon uptime"><Clock size={18} /></div>
              <div>
                <div className="info-card-title">System Uptime</div>
                <div className="info-card-subtitle">Active running session</div>
              </div>
            </div>
          </div>
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '6px' }}>
              {loadInfo?.uptime_formatted || '—'}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-muted)' }}>
              <span className="status-indicator status-active" />
              <span>
                <strong style={{ color: 'var(--text-secondary)' }}>{data?.processes?.length || 0}</strong> total system processes
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Toolbar ────────────────────────────────────────────── */}
      <div className="toolbar processes-toolbar">
        <div className="processes-search-wrap">
          <Search size={15} className="processes-search-icon" />
          <input
            type="search"
            className="form-input processes-search-input"
            placeholder="Search by PID, name, user, or cmd (e.g. chrome, python)..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setCurrentPage(1); }}
          />
        </div>

        <div className="processes-filter-grid">
          {/* User filter */}
          <div className="processes-filter-item">
            <label htmlFor="user-filter" className="form-label processes-filter-label">User:</label>
            <CustomSelect
              id="user-filter"
              options={userOptions}
              value={userFilter}
              onChange={(val) => { setUserFilter(val); setCurrentPage(1); }}
              searchable={uniqueUsers.length > 5}
              className="processes-filter-select"
            />
          </div>

          {/* Sort filter */}
          <div className="processes-filter-item">
            <label htmlFor="sort-filter" className="form-label processes-filter-label">Sort:</label>
            <CustomSelect
              id="sort-filter"
              options={sortOptions}
              value={sortBy}
              onChange={(val) => handleSortDropdown(val as 'mem' | 'cpu' | 'pid' | 'name')}
              className="processes-filter-select"
            />
          </div>

          {/* Show / limit filter */}
          <div className="processes-filter-item">
            <label htmlFor="show-limit" className="form-label processes-filter-label">Show:</label>
            <CustomSelect
              id="show-limit"
              options={showOptions}
              value={pageSize}
              onChange={(val) => { setPageSize(val === 'all' ? 'all' : Number(val)); setCurrentPage(1); }}
              className="processes-filter-select"
            />
          </div>

          {/* Refresh & Auto-refresh actions */}
          <div className="processes-filter-item processes-filter-btn-item">
            <label className="processes-autorefresh-label">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                style={{ accentColor: 'var(--purple)' }}
              />
              Auto (5s)
            </label>
            <button
              className="btn btn-secondary processes-refresh-btn"
              onClick={() => loadProcesses(true)}
              disabled={loading || refreshing}
            >
              <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </div>

      {/* ── Table Card ─────────────────────────────────────────── */}
      <div className="card processes-card">
        <div className="card-header processes-card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h3 style={{ margin: 0, fontSize: '1.05rem' }}>Processes ({data?.processes?.length || 0})</h3>
            {filteredProcesses.length !== (data?.processes?.length || 0) && (
              <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                ({filteredProcesses.length} matching filter)
              </span>
            )}
          </div>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Page {currentPage} of {totalPages}</span>
        </div>

        <div className="card-body" style={{ padding: 0 }}>
          <div className="table-scroll-wrap processes-table-wrap">
            <ProcessTable
              processes={paginatedProcesses}
              loading={loading}
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={handleSort}
              expandedPid={expandedPid}
              onToggleExpand={(pid) => setExpandedPid(expandedPid === pid ? null : pid)}
              onKill={(p) => setPendingKill(p)}
              onCopy={handleCopy}
              copiedKey={copiedType}
            />
          </div>

          {/* Pagination Footer */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderTop: '1px solid var(--border)', flexWrap: 'wrap', gap: '8px' }}>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              {filteredProcesses.length === 0 ? 'No processes found' : `Showing ${effectivePageSize === Infinity ? 1 : (currentPage - 1) * effectivePageSize + 1} to ${effectivePageSize === Infinity ? filteredProcesses.length : Math.min(currentPage * effectivePageSize, filteredProcesses.length)} of ${filteredProcesses.length} processes`}
            </span>
            {totalPages > 1 && (
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <button className="btn btn-xs btn-secondary" onClick={() => setCurrentPage((p) => Math.max(1, p - 1))} disabled={currentPage <= 1}>
                  ← Previous
                </button>
                <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', padding: '0 4px' }}>Page {currentPage} of {totalPages}</span>
                <button className="btn btn-xs btn-secondary" onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))} disabled={currentPage >= totalPages}>
                  Next →
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Confirm Kill Modal ─────────────────────────────────── */}
      {pendingKill && (
        <ConfirmModal
          isOpen={Boolean(pendingKill)}
          onClose={() => setPendingKill(null)}
          onConfirm={handleConfirmKill}
          isLoading={killLoading}
          isDanger={true}
          title="Terminate Process"
          message={`Are you sure you want to send SIGKILL to '${pendingKill.name || pendingKill.command}' (PID: ${pendingKill.pid})? Unsaved data in this process will be lost.`}
          confirmLabel="Terminate (SIGKILL)"
        />
      )}
    </div>
  );
};
