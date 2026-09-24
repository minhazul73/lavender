import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { api } from '../../api/client';
import { ProcessItem, ProcessesOverviewResponse } from '../../api/types';
import { useToast } from '../../context/ToastContext';
import { ConfirmModal } from '../../components/common/ConfirmModal';
import {
  Activity,
  Search,
  RefreshCw,
  XCircle,
  ArrowUpDown,
  Cpu,
  Layers,
} from 'lucide-react';

export const ProcessesPage: React.FC = () => {
  const { addToast } = useToast();
  const [data, setData] = useState<ProcessesOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Filters & sorting
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<'cpu' | 'mem' | 'pid' | 'name'>('cpu');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [pageSize, setPageSize] = useState<number>(50);
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Kill process state
  const [pendingKill, setPendingKill] = useState<ProcessItem | null>(null);
  const [killLoading, setKillLoading] = useState(false);

  const loadProcesses = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const res = await api.get<ProcessesOverviewResponse>(
        `/api/system/processes?sort_by=${sortBy}&limit=200`
      );
      setData(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch processes';
      addToast(msg, 'error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [sortBy, addToast]);

  useEffect(() => {
    loadProcesses();
  }, [loadProcesses]);

  // Auto-refresh interval (5s)
  useEffect(() => {
    if (!autoRefresh) return;
    const timer = setInterval(() => {
      if (!document.hidden) {
        loadProcesses(true);
      }
    }, 5000);
    return () => clearInterval(timer);
  }, [autoRefresh, loadProcesses]);

  // Filter & sort processes
  const filteredProcesses = useMemo(() => {
    if (!data?.processes) return [];
    return data.processes
      .filter((p) => {
        if (!search.trim()) return true;
        const q = search.toLowerCase();
        return (
          p.name.toLowerCase().includes(q) ||
          p.command.toLowerCase().includes(q) ||
          p.user.toLowerCase().includes(q) ||
          String(p.pid).includes(q)
        );
      })
      .sort((a, b) => {
        let valA = a[sortBy];
        let valB = b[sortBy];
        if (typeof valA === 'string') valA = (valA as string).toLowerCase();
        if (typeof valB === 'string') valB = (valB as string).toLowerCase();

        if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
        if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
        return 0;
      });
  }, [data?.processes, search, sortBy, sortOrder]);

  const totalPages = Math.ceil(filteredProcesses.length / pageSize) || 1;
  const paginatedProcesses = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredProcesses.slice(start, start + pageSize);
  }, [filteredProcesses, currentPage, pageSize]);

  // Handle Sort Change
  const handleSort = (field: 'cpu' | 'mem' | 'pid' | 'name') => {
    if (sortBy === field) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
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
        addToast(`Process ${pendingKill.name} (PID ${pendingKill.pid}) terminated`, 'success');
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

  const loadInfo = data?.load as Record<string, number> | undefined;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* ── Load Summary Cards ─────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        <div className="card" style={{ padding: '14px 18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--purple)', marginBottom: '6px' }}>
            <Cpu size={16} />
            <span style={{ fontSize: '0.82rem', fontWeight: 600 }}>Load Average</span>
          </div>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'baseline' }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>1m: </span>
              <strong className="font-mono">{loadInfo?.['1m'] ?? loadInfo?.load1 ?? '—'}</strong>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>5m: </span>
              <strong className="font-mono">{loadInfo?.['5m'] ?? loadInfo?.load5 ?? '—'}</strong>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>15m: </span>
              <strong className="font-mono">{loadInfo?.['15m'] ?? loadInfo?.load15 ?? '—'}</strong>
            </div>
          </div>
        </div>

        <div className="card" style={{ padding: '14px 18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--blue)', marginBottom: '6px' }}>
            <Layers size={16} />
            <span style={{ fontSize: '0.82rem', fontWeight: 600 }}>Active Tasks</span>
          </div>
          <div style={{ display: 'flex', gap: '14px', alignItems: 'baseline' }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total: </span>
              <strong className="font-mono">{data?.processes?.length || 0}</strong>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Filtered: </span>
              <strong className="font-mono">{filteredProcesses.length}</strong>
            </div>
          </div>
        </div>
      </div>

      {/* ── Toolbar ────────────────────────────────────────────── */}
      <div className="toolbar" style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: '1 1 240px', maxWidth: '380px' }}>
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
            placeholder="Search by PID, name, user, or cmd..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setCurrentPage(1);
            }}
            style={{ paddingLeft: '36px' }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <label className="form-label" style={{ margin: 0, fontSize: '0.82rem' }}>
            Show:
          </label>
          <select
            className="form-select"
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setCurrentPage(1);
            }}
            style={{ width: 'auto' }}
          >
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              style={{ accentColor: 'var(--purple)' }}
            />
            Auto-refresh (5s)
          </label>
        </div>

        <button
          className="btn btn-secondary"
          onClick={() => loadProcesses(true)}
          disabled={loading || refreshing}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* ── Table Card ─────────────────────────────────────────── */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Activity size={18} color="var(--orange)" />
            <h3 style={{ margin: 0, fontSize: '1.05rem' }}>Running Processes</h3>
          </div>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Page {currentPage} of {totalPages}
          </span>
        </div>

        <div className="card-body" style={{ padding: 0 }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th style={{ cursor: 'pointer' }} onClick={() => handleSort('pid')}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      PID <ArrowUpDown size={12} />
                    </span>
                  </th>
                  <th>User</th>
                  <th style={{ cursor: 'pointer' }} onClick={() => handleSort('name')}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      Process / Command <ArrowUpDown size={12} />
                    </span>
                  </th>
                  <th style={{ cursor: 'pointer', width: '130px' }} onClick={() => handleSort('cpu')}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      CPU % <ArrowUpDown size={12} />
                    </span>
                  </th>
                  <th style={{ cursor: 'pointer', width: '130px' }} onClick={() => handleSort('mem')}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      MEM % <ArrowUpDown size={12} />
                    </span>
                  </th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                      Loading process table…
                    </td>
                  </tr>
                ) : paginatedProcesses.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                      No matching processes found.
                    </td>
                  </tr>
                ) : (
                  paginatedProcesses.map((p) => {
                    const isHighCpu = p.cpu > 50;
                    const isHighMem = p.mem > 50;
                    return (
                      <tr key={p.pid}>
                        <td className="font-mono" style={{ fontSize: '0.85rem' }}>
                          {p.pid}
                        </td>
                        <td style={{ color: 'var(--text-secondary)' }}>{p.user}</td>
                        <td style={{ maxWidth: '380px' }}>
                          <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <strong style={{ color: 'var(--text-primary)', fontSize: '0.88rem' }}>
                              {p.name}
                            </strong>
                            <span
                              style={{
                                fontSize: '0.75rem',
                                color: 'var(--text-muted)',
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                              }}
                              title={p.command}
                            >
                              {p.command}
                            </span>
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span
                              className="font-mono"
                              style={{
                                minWidth: '42px',
                                color: isHighCpu ? '#f87171' : 'inherit',
                                fontWeight: isHighCpu ? 600 : 400,
                              }}
                            >
                              {p.cpu.toFixed(1)}%
                            </span>
                            <div className="progress-bar-outer" style={{ height: '4px', flex: 1 }}>
                              <div
                                className={`progress-bar-inner ${isHighCpu ? 'crit' : ''}`}
                                style={{ width: `${Math.min(100, p.cpu)}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span
                              className="font-mono"
                              style={{
                                minWidth: '42px',
                                color: isHighMem ? '#fbbf24' : 'inherit',
                                fontWeight: isHighMem ? 600 : 400,
                              }}
                            >
                              {p.mem.toFixed(1)}%
                            </span>
                            <div className="progress-bar-outer" style={{ height: '4px', flex: 1 }}>
                              <div
                                className={`progress-bar-inner ${isHighMem ? 'warn' : ''}`}
                                style={{ width: `${Math.min(100, p.mem)}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <button
                            className="btn btn-xs btn-danger"
                            title="Kill Process"
                            onClick={() => setPendingKill(p)}
                            style={{ padding: '4px 8px' }}
                          >
                            <XCircle size={13} style={{ marginRight: '4px' }} />
                            <span>Kill</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          {totalPages > 1 && (
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '12px 16px',
                borderTop: '1px solid var(--border)',
              }}
            >
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Showing {(currentPage - 1) * pageSize + 1} to{' '}
                {Math.min(currentPage * pageSize, filteredProcesses.length)} of {filteredProcesses.length}
              </span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  className="btn btn-xs btn-secondary"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage <= 1}
                >
                  ← Previous
                </button>
                <button
                  className="btn btn-xs btn-secondary"
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage >= totalPages}
                >
                  Next →
                </button>
              </div>
            </div>
          )}
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
          message={`Are you sure you want to send SIGKILL to '${pendingKill.name}' (PID: ${pendingKill.pid})? Unsaved data in this process will be lost.`}
          confirmLabel="Terminate (SIGKILL)"
        />
      )}
    </div>
  );
};
