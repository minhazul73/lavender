import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../api/client';
import { StorageOverviewResponse, StorageDiskItem } from '../../api/types';
import { useToast } from '../../context/ToastContext';
import { ConfirmModal } from '../../components/common/ConfirmModal';
import { FileBrowser } from './FileBrowser';
import {
  HardDrive,
  RefreshCw,
  Disc,
  Unplug,
  FolderTree,
  Layers,
} from 'lucide-react';

export const StoragePage: React.FC = () => {
  const { addToast } = useToast();
  const [data, setData] = useState<StorageOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Active view tab: 'browser' (File Browser) or 'disks' (Partitions & Mounts)
  const [activeTab, setActiveTab] = useState<'browser' | 'disks'>('browser');

  // Unmount modal
  const [pendingUnmount, setPendingUnmount] = useState<StorageDiskItem | null>(null);
  const [unmountLoading, setUnmountLoading] = useState(false);

  const loadStorage = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const res = await api.get<StorageOverviewResponse>('/api/system/storage');
      setData(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch storage info';
      addToast(msg, 'error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [addToast]);

  useEffect(() => {
    loadStorage();
  }, [loadStorage]);

  const handleConfirmUnmount = async () => {
    if (!pendingUnmount) return;
    setUnmountLoading(true);
    const mountTarget = pendingUnmount.mount_point || pendingUnmount.mount || '';
    try {
      const res = await api.post<{ success: boolean; message?: string }>(
        `/api/storage/unmount?mount_point=${encodeURIComponent(mountTarget)}`
      );
      if (res.success) {
        addToast(`Successfully unmounted ${mountTarget}`, 'success');
        setPendingUnmount(null);
        await loadStorage(true);
      } else {
        addToast(res.message || 'Failed to unmount disk', 'error');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unmount operation failed';
      addToast(msg, 'error');
    } finally {
      setUnmountLoading(false);
    }
  };

  const disks = data?.disks || [];

  return (
    <div className="file-browser-container">
      {/* ── Toolbar & View Switcher Tabs ─────────────────────────── */}
      <div className="storage-page-header">
        <div className="storage-page-header-title">
          <div className="storage-page-header-icon">
            <HardDrive size={22} />
          </div>
          <div>
            <div className="storage-page-title-row">
              <h2 className="storage-page-title">
                Storage & Filesystems
              </h2>
              <span className="badge badge-lavender">{disks.length} Mounts</span>
            </div>
            <p className="storage-page-subtitle">
              Explore files, inspect storage devices, and manage Linux filesystem partitions
            </p>
          </div>
        </div>

        <div className="storage-page-header-actions">
          {/* Segmented View Switcher Tabs */}
          <div className="storage-view-tabs">
            <button
              className={`storage-view-tab ${activeTab === 'browser' ? 'active' : ''}`}
              onClick={() => setActiveTab('browser')}
            >
              <FolderTree size={16} />
              <span>File Browser</span>
            </button>
            <button
              className={`storage-view-tab ${activeTab === 'disks' ? 'active' : ''}`}
              onClick={() => setActiveTab('disks')}
            >
              <Layers size={16} />
              <span>Partitions & Disks</span>
            </button>
          </div>

          <button
            className="btn btn-secondary storage-refresh-btn"
            onClick={() => loadStorage(true)}
            disabled={loading || refreshing}
            title="Refresh storage information"
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* ── Tab 1: File Browser ─────────────────────────────────── */}
      {activeTab === 'browser' && (
        <FileBrowser
          disks={disks}
          onUnmountClick={(d) => setPendingUnmount(d)}
          onRefreshStorage={() => loadStorage(true)}
        />
      )}

      {/* ── Tab 2: Disks & Partitions ───────────────────────────── */}
      {activeTab === 'disks' && (
        <div className="storage-disks-container">
          {/* Partition Cards Grid */}
          <div className="storage-disks-grid">
            {loading ? (
              <div
                className="card"
                style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}
              >
                Inspecting mounted filesystems…
              </div>
            ) : disks.length === 0 ? (
              <div
                className="card"
                style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}
              >
                No storage devices detected.
              </div>
            ) : (
              disks.map((d, idx) => {
                const pct =
                  typeof d.pct_num === 'number'
                    ? d.pct_num
                    : parseInt(String(d.use_percent || d.use_pct || '0').replace('%', ''), 10) || 0;
                const mount = d.mount_point || d.mount || '/';
                const filesystem = d.filesystem || d.fs || 'unknown';
                const available = d.available || d.avail || '—';
                const isRoot = mount === '/' || mount === '/boot';
                const isCrit = pct > 85;
                const isWarn = pct > 70;

                return (
                  <div
                    key={mount || idx}
                    className="card storage-disk-card"
                    style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div
                          style={{
                            width: '36px',
                            height: '36px',
                            borderRadius: '8px',
                            background: 'rgba(124, 58, 237, 0.12)',
                            color: 'var(--purple)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          <Disc size={20} />
                        </div>
                        <div>
                          <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 600 }}>
                            {mount}
                          </h4>
                          <span
                            className="font-mono"
                            style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}
                          >
                            {filesystem}
                          </span>
                        </div>
                      </div>

                      {!isRoot && (
                        <button
                          className="btn btn-xs btn-ghost"
                          title="Unmount Partition"
                          onClick={() => setPendingUnmount({ ...d, mount_point: mount, filesystem })}
                          style={{ color: '#f87171' }}
                        >
                          <Unplug size={14} style={{ marginRight: '4px' }} />
                          <span>Unmount</span>
                        </button>
                      )}
                    </div>

                    <div>
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          fontSize: '0.82rem',
                          marginBottom: '6px',
                        }}
                      >
                        <span style={{ color: 'var(--text-secondary)' }}>
                          Used: <strong style={{ color: 'var(--text-primary)' }}>{d.used || '—'}</strong> /{' '}
                          {d.size || '—'}
                        </span>
                        <span
                          className="font-mono"
                          style={{
                            fontWeight: 600,
                            color: isCrit ? '#f87171' : isWarn ? '#fbbf24' : 'var(--text-secondary)',
                          }}
                        >
                          {pct}%
                        </span>
                      </div>

                      <div className="progress-bar-outer" style={{ height: '7px' }}>
                        <div
                          className={`progress-bar-inner ${isCrit ? 'crit' : isWarn ? 'warn' : ''}`}
                          style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
                        />
                      </div>
                    </div>

                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        fontSize: '0.75rem',
                        color: 'var(--text-muted)',
                        paddingTop: '6px',
                        borderTop: '1px solid var(--border-subtle)',
                      }}
                    >
                      <span>
                        Free space: <strong style={{ color: 'var(--text-secondary)' }}>{available}</strong>
                      </span>
                      <span>Type: {filesystem.startsWith('/dev') ? 'Physical Block' : 'Virtual / Pseudo'}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Table Overview */}
          <div className="card">
            <div className="card-header">
              <h3 style={{ margin: 0, fontSize: '1rem' }}>Mounted Partition Table</h3>
            </div>
            <div className="card-body" style={{ padding: 0 }}>
              <div className="storage-table-wrapper" style={{ overflowX: 'auto' }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Mount Point</th>
                      <th>Device / Filesystem</th>
                      <th>Total Size</th>
                      <th>Used</th>
                      <th>Available</th>
                      <th>Capacity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {disks.map((d, idx) => {
                      const mount = d.mount_point || d.mount || '/';
                      const filesystem = d.filesystem || d.fs || 'unknown';
                      const available = d.available || d.avail || '—';
                      const usePercent =
                        d.use_percent || d.use_pct || (typeof d.pct_num === 'number' ? `${d.pct_num}%` : '—');
                      return (
                        <tr key={mount || idx}>
                          <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{mount}</td>
                          <td className="font-mono" style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                            {filesystem}
                          </td>
                          <td className="font-mono">{d.size || '—'}</td>
                          <td className="font-mono" style={{ color: 'var(--purple)' }}>{d.used || '—'}</td>
                          <td className="font-mono" style={{ color: 'var(--green)' }}>{available}</td>
                          <td>
                            <span className="badge badge-lavender">{usePercent}</span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Confirm Unmount Modal ──────────────────────────────── */}
      {pendingUnmount && (
        <ConfirmModal
          isOpen={Boolean(pendingUnmount)}
          onClose={() => setPendingUnmount(null)}
          onConfirm={handleConfirmUnmount}
          isLoading={unmountLoading}
          isDanger={true}
          title="Unmount Filesystem"
          message={`Are you sure you want to unmount '${pendingUnmount.mount_point || pendingUnmount.mount || ''}' (${pendingUnmount.filesystem || pendingUnmount.fs || 'device'})? Any open files on this drive will be terminated.`}
          confirmLabel="Unmount Partition"
        />
      )}
    </div>
  );
};
