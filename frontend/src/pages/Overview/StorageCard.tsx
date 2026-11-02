import React from 'react';
import { Link } from 'react-router-dom';
import { HardDrive } from 'lucide-react';
import type { StorageDiskItem } from '../../api/types';

export interface StorageCardProps {
  disks?: StorageDiskItem[];
}

export const StorageCard: React.FC<StorageCardProps> = ({ disks }) => {
  return (
    <section className="card card-storage" style={{ position: 'relative' }}>
      <div className="card-header">
        <span className="card-icon card-icon-disk">
          <HardDrive size={13} />
        </span>
        <span className="card-title">STORAGE</span>
        <Link to="/storage" className="card-link" style={{ marginLeft: 'auto' }}>
          →
        </Link>
      </div>
      <div className="card-body store-card-body">
        <div id="store-mounts" className="store-mounts-container">
          {disks && disks.length > 0 ? (
            disks
              .filter((d) => {
                const m = (d.mount || d.mount_point || '').toLowerCase();
                return !m.includes('efivars') && !m.includes('credentials');
              })
              .slice(0, 3)
              .sort((a, b) => (Number(a.is_external || false) - Number(b.is_external || false)) || ((a.mount || a.mount_point || '') > (b.mount || b.mount_point || '') ? 1 : -1))
              .map((d) => {
                const pct =
                  typeof d.pct_num === 'number'
                    ? d.pct_num
                    : parseInt(String(d.use_pct || d.use_percent || '0').replace('%', ''), 10) || 0;
                const mount = d.mount || d.mount_point || '/';
                const mountDisplay = mount === '/' ? 'System (/)' : mount;
                const icon = d.is_external ? '💾' : '📁';
                const barClass = pct > 90 ? ' crit' : pct > 80 ? ' warn' : '';
                const used = d.used || '?';
                const total = d.size || '?';
                const avail = d.avail || d.available || '?';

                return (
                  <div key={mount} className={`store-mount ${d.is_external ? 'is-external' : ''}`}>
                    <div className="store-mount-header">
                      <span className="store-mount-icon">{icon}</span>
                      <span className="store-mount-label">{mountDisplay}</span>
                      <span className="store-mount-pct">{pct}%</span>
                    </div>
                    <div className="store-mount-detail">
                      {used} / {total} · {avail} free
                    </div>
                    <div className="store-mount-bar-wrap">
                      <div className={`store-mount-bar${barClass}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })
          ) : (
            <>
              <div className="store-mount">
                <div className="store-mount-header">
                  <span className="store-mount-icon">📁</span>
                  <span className="store-mount-label">System (/)</span>
                  <span className="store-mount-pct">50%</span>
                </div>
                <div className="store-mount-detail">22.9G / 48.8G · 23.4G free</div>
                <div className="store-mount-bar-wrap">
                  <div className="store-mount-bar" style={{ width: '50%' }} />
                </div>
              </div>
              <div className="store-mount">
                <div className="store-mount-header">
                  <span className="store-mount-icon">📁</span>
                  <span className="store-mount-label">/boot/efi</span>
                  <span className="store-mount-pct">8%</span>
                </div>
                <div className="store-mount-detail">38M / 508M · 470M free</div>
                <div className="store-mount-bar-wrap">
                  <div className="store-mount-bar" style={{ width: '8%' }} />
                </div>
              </div>
              <div className="store-mount is-external">
                <div className="store-mount-header">
                  <span className="store-mount-icon">💾</span>
                  <span className="store-mount-label">/mnt/sdcard</span>
                  <span className="store-mount-pct">70%</span>
                </div>
                <div className="store-mount-detail">43.2G / 58.2G · 12.0G free</div>
                <div className="store-mount-bar-wrap">
                  <div className="store-mount-bar" style={{ width: '70%' }} />
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
};

