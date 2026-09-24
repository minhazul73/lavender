import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { api } from '../../api/client';
import { ServiceItem, ServicesListResponse } from '../../api/types';
import { useToast } from '../../context/ToastContext';
import { Modal } from '../../components/common/Modal';
import { ConfirmModal } from '../../components/common/ConfirmModal';
import {
  Server,
  Search,
  RefreshCw,
  Play,
  Square,
  RotateCw,
  FileText,
  CheckCircle2,
  XCircle,
  HelpCircle,
} from 'lucide-react';

export const ServicesPage: React.FC = () => {
  const { addToast } = useToast();
  const [services, setServices] = useState<ServiceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Filters & Pagination
  const [search, setSearch] = useState('');
  const [scopeFilter, setScopeFilter] = useState<'all' | 'user' | 'system'>('all');
  const [stateFilter, setStateFilter] = useState<string>('');
  const [pageSize, setPageSize] = useState<number>(50);
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Action modal confirmation
  const [pendingAction, setPendingAction] = useState<{
    unit: string;
    action: 'start' | 'stop' | 'restart';
    isUser: boolean;
  } | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Logs modal
  const [selectedLogsUnit, setSelectedLogsUnit] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

  const loadServices = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const res = await api.get<ServicesListResponse>('/api/system/services');
      setServices(res.services || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load services';
      addToast(msg, 'error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [addToast]);

  useEffect(() => {
    loadServices();
  }, [loadServices]);

  // Filtered & paginated services
  const filteredServices = useMemo(() => {
    return services.filter((s) => {
      // Scope
      if (scopeFilter !== 'all') {
        const isUser = s.scope === 'user' || s.unit.includes('@');
        if (scopeFilter === 'user' && !isUser) return false;
        if (scopeFilter === 'system' && isUser) return false;
      }

      // State
      if (stateFilter) {
        const st = (s.active || '').toLowerCase();
        if (stateFilter === 'active' && st !== 'active') return false;
        if (stateFilter === 'inactive' && st !== 'inactive') return false;
        if (stateFilter === 'failed' && st !== 'failed') return false;
      }

      // Search
      if (search.trim()) {
        const q = search.toLowerCase();
        const matchesUnit = s.unit.toLowerCase().includes(q);
        const matchesDesc = (s.description || '').toLowerCase().includes(q);
        if (!matchesUnit && !matchesDesc) return false;
      }

      return true;
    });
  }, [services, scopeFilter, stateFilter, search]);

  const totalPages = Math.ceil(filteredServices.length / pageSize) || 1;
  const paginatedServices = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredServices.slice(start, start + pageSize);
  }, [filteredServices, currentPage, pageSize]);

  // Execute Service Action (Start, Stop, Restart)
  const handleExecuteAction = async () => {
    if (!pendingAction) return;
    setActionLoading(true);
    try {
      const res = await api.post<{ success: boolean; output?: string }>('/api/system/services/action', {
        service: pendingAction.unit,
        action: pendingAction.action,
        user: pendingAction.isUser,
      });

      if (res.success) {
        addToast(`Service ${pendingAction.unit} ${pendingAction.action}ed successfully`, 'success');
        setPendingAction(null);
        await loadServices(true);
      } else {
        addToast(res.output || `Failed to ${pendingAction.action} service`, 'error');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : `Failed to execute ${pendingAction.action}`;
      addToast(msg, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // View Service Logs
  const handleOpenLogs = async (unit: string) => {
    setSelectedLogsUnit(unit);
    setLogsLoading(true);
    setLogs([]);
    try {
      const res = await api.get<{ logs?: string[] }>(`/api/system/logs?service=${encodeURIComponent(unit)}&limit=100`);
      setLogs(res.logs || ['No journal entries found for this service.']);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch service logs';
      setLogs([`Error reading journalctl logs: ${msg}`]);
    } finally {
      setLogsLoading(false);
    }
  };

  const getStatusBadge = (active?: string) => {
    const s = (active || '').toLowerCase();
    if (s === 'active') {
      return (
        <span className="badge badge-success" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
          <CheckCircle2 size={12} /> Active
        </span>
      );
    }
    if (s === 'failed') {
      return (
        <span className="badge badge-danger" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
          <XCircle size={12} /> Failed
        </span>
      );
    }
    return (
      <span className="badge badge-warning" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
        <HelpCircle size={12} /> {active || 'Inactive'}
      </span>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
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
            placeholder="Search services (e.g. ssh, nginx, lavender)..."
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
            Scope:
          </label>
          <select
            className="form-select"
            value={scopeFilter}
            onChange={(e) => {
              setScopeFilter(e.target.value as 'all' | 'user' | 'system');
              setCurrentPage(1);
            }}
            style={{ width: 'auto' }}
          >
            <option value="all">All Services</option>
            <option value="user">User Only</option>
            <option value="system">System Only</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <label className="form-label" style={{ margin: 0, fontSize: '0.82rem' }}>
            State:
          </label>
          <select
            className="form-select"
            value={stateFilter}
            onChange={(e) => {
              setStateFilter(e.target.value);
              setCurrentPage(1);
            }}
            style={{ width: 'auto' }}
          >
            <option value="">All States</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="failed">Failed</option>
          </select>
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

        <button
          className="btn btn-secondary"
          onClick={() => loadServices(true)}
          disabled={loading || refreshing}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* ── Services Table Card ────────────────────────────────── */}
      <div className="card">
        <div
          className="card-header"
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Server size={18} color="var(--purple)" />
            <h3 style={{ margin: 0, fontSize: '1.05rem' }}>
              System Services ({filteredServices.length})
            </h3>
          </div>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Showing page {currentPage} of {totalPages}
          </span>
        </div>

        <div className="card-body" style={{ padding: 0 }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Unit Name</th>
                  <th>Scope</th>
                  <th>Load</th>
                  <th>Active State</th>
                  <th>Sub</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                      Loading systemd services…
                    </td>
                  </tr>
                ) : paginatedServices.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                      No matching services found.
                    </td>
                  </tr>
                ) : (
                  paginatedServices.map((s) => {
                    const isUser = s.scope === 'user';
                    const isActive = (s.active || '').toLowerCase() === 'active';
                    return (
                      <tr key={s.unit}>
                        <td>
                          <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{s.unit}</span>
                            {s.description && (
                              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                {s.description}
                              </span>
                            )}
                          </div>
                        </td>
                        <td>
                          <span
                            className="badge"
                            style={{
                              background: isUser ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                              color: isUser ? '#38bdf8' : 'var(--text-secondary)',
                            }}
                          >
                            {s.scope || 'system'}
                          </span>
                        </td>
                        <td style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{s.load || '—'}</td>
                        <td>{getStatusBadge(s.active)}</td>
                        <td className="font-mono" style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                          {s.sub || '—'}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', gap: '6px' }}>
                            {isActive ? (
                              <>
                                <button
                                  className="btn btn-xs btn-secondary"
                                  title="Restart Service"
                                  onClick={() =>
                                    setPendingAction({ unit: s.unit, action: 'restart', isUser })
                                  }
                                >
                                  <RotateCw size={13} />
                                </button>
                                <button
                                  className="btn btn-xs btn-danger"
                                  title="Stop Service"
                                  onClick={() =>
                                    setPendingAction({ unit: s.unit, action: 'stop', isUser })
                                  }
                                >
                                  <Square size={13} />
                                </button>
                              </>
                            ) : (
                              <button
                                className="btn btn-xs btn-primary"
                                title="Start Service"
                                onClick={() =>
                                  setPendingAction({ unit: s.unit, action: 'start', isUser })
                                }
                              >
                                <Play size={13} />
                              </button>
                            )}
                            <button
                              className="btn btn-xs btn-ghost"
                              title="View Journal Logs"
                              onClick={() => handleOpenLogs(s.unit)}
                            >
                              <FileText size={13} />
                            </button>
                          </div>
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
                {Math.min(currentPage * pageSize, filteredServices.length)} of {filteredServices.length}
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

      {/* ── Action Confirmation Modal ──────────────────────────── */}
      {pendingAction && (
        <ConfirmModal
          isOpen={Boolean(pendingAction)}
          onClose={() => setPendingAction(null)}
          onConfirm={handleExecuteAction}
          isLoading={actionLoading}
          isDanger={pendingAction.action === 'stop'}
          title={`${pendingAction.action.toUpperCase()} Service`}
          message={`Are you sure you want to ${pendingAction.action} unit '${pendingAction.unit}'?`}
          confirmLabel={`${pendingAction.action.charAt(0).toUpperCase() + pendingAction.action.slice(1)} Service`}
        />
      )}

      {/* ── Journalctl Logs Modal ──────────────────────────────── */}
      {selectedLogsUnit && (
        <Modal
          isOpen={Boolean(selectedLogsUnit)}
          onClose={() => setSelectedLogsUnit(null)}
          maxWidth="760px"
          title={
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={18} color="var(--purple)" /> Logs: {selectedLogsUnit}
            </span>
          }
        >
          <div
            style={{
              background: 'rgba(0, 0, 0, 0.4)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '0.78rem',
              color: 'var(--text-secondary)',
              maxHeight: '400px',
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
            }}
          >
            {logsLoading ? (
              <div style={{ color: 'var(--text-muted)' }}>Fetching journalctl log entries…</div>
            ) : logs.length > 0 ? (
              logs.map((line, idx) => (
                <div key={idx} style={{ padding: '2px 0' }}>
                  {line}
                </div>
              ))
            ) : (
              <div>No log lines captured.</div>
            )}
          </div>
          <div className="modal-footer" style={{ marginTop: '16px' }}>
            <button
              className="btn btn-secondary"
              onClick={() => handleOpenLogs(selectedLogsUnit)}
              disabled={logsLoading}
            >
              Refresh Logs
            </button>
            <button className="btn btn-primary" onClick={() => setSelectedLogsUnit(null)}>
              Close
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
};
