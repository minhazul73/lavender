import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../api/client';
import { StorageOverviewResponse, StorageDiskItem } from '../../api/types';
import { useToast } from '../../context/ToastContext';
import { ConfirmModal } from '../../components/common/ConfirmModal';
import { HardDrive, RefreshCw, Disc, Unplug } from 'lucide-react';

export const StoragePage: React.FC = () => {
  const { addToast } = useToast();
  const [data, setData] = useState<StorageOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

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
    try {
      const res = await api.post<{ success: boolean; message?: string }>(
        `/api/storage/unmount?mount_point=${encodeURIComponent(pendingUnmount.mount_point)}`
      );
      if (res.success) {
        addToast(`Successfully unmounted ${pendingUnmount.mount_point}`, 'success');
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* ── Toolbar ────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <HardDrive size={22} color="var(--purple)" />
          <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700 }}>Storage & Partitions</h2>
          <span className="badge badge-lavender">{disks.length} Mounts</span>
        </div>

        <button
          className="btn btn-secondary"
          onClick={() => loadStorage(true)}
          disabled={loading || refreshing}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* ── Partition Cards Grid ───────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
        {loading ? (
          <div className="card" style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
            Inspecting mounted filesystems…
          </div>
        ) : disks.length === 0 ? (
          <div className="card" style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No storage devices detected.
          </div>
        ) : (
          disks.map((d) => {
            const pct = parseInt(d.use_percent.replace('%', ''), 10) || 0;
            const isRoot = d.mount_point === '/' || d.mount_point === '/boot';
            const isCrit = pct > 85;
            const isWarn = pct > 70;

            return (
              <div key={d.mount_point} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
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
                      <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 600 }}>{d.mount_point}</h4>
                      <span className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {d.filesystem}
                      </span>
                    </div>
                  </div>

                  {!isRoot && (
                    <button
                      className="btn btn-xs btn-ghost"
                      title="Unmount Partition"
                      onClick={() => setPendingUnmount(d)}
                      style={{ color: '#f87171' }}
                    >
                      <Unplug size={14} style={{ marginRight: '4px' }} />
                      <span>Unmount</span>
                    </button>
                  )}
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '6px' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>
                      Used: <strong style={{ color: 'var(--text-primary)' }}>{d.used}</strong> / {d.size}
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
                      style={{ width: `${Math.min(100, pct)}%` }}
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
                  <span>Free space: <strong style={{ color: 'var(--text-secondary)' }}>{d.available}</strong></span>
                  <span>Type: {d.filesystem.startsWith('/dev') ? 'Physical Block' : 'Virtual / Pseudo'}</span>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* ── Table Overview ─────────────────────────────────────── */}
      <div className="card">
        <div className="card-header">
          <h3 style={{ margin: 0, fontSize: '1rem' }}>Mounted Partition Table</h3>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          <div style={{ overflowX: 'auto' }}>
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
                {disks.map((d) => (
                  <tr key={d.mount_point}>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{d.mount_point}</td>
                    <td className="font-mono" style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                      {d.filesystem}
                    </td>
                    <td className="font-mono">{d.size}</td>
                    <td className="font-mono" style={{ color: 'var(--purple)' }}>{d.used}</td>
                    <td className="font-mono" style={{ color: 'var(--green)' }}>{d.available}</td>
                    <td>
                      <span className="badge badge-lavender">{d.use_percent}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── Confirm Unmount Modal ──────────────────────────────── */}
      {pendingUnmount && (
        <ConfirmModal
          isOpen={Boolean(pendingUnmount)}
          onClose={() => setPendingUnmount(null)}
          onConfirm={handleConfirmUnmount}
          isLoading={unmountLoading}
          isDanger={true}
          title="Unmount Filesystem"
          message={`Are you sure you want to unmount '${pendingUnmount.mount_point}' (${pendingUnmount.filesystem})? Any open files on this drive will be terminated.`}
          confirmLabel="Unmount Partition"
        />
      )}
    </div>
  );
};
