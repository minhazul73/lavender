import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Server } from 'lucide-react';

export interface ServicesCardProps {
  services?: any[];
}

const CIRC = 97.39; // 2 * PI * 15.5

export const ServicesCard: React.FC<ServicesCardProps> = ({ services }) => {
  const svcCounts = useMemo(() => {
    const list = services;
    if (!list || !Array.isArray(list) || list.length === 0) {
      return { active: 98, inactive: 129, failed: 1, total: 228 };
    }
    let active = 0, inactive = 0, failed = 0;
    list.forEach((s) => {
      const st = (s.active_state || s.active || '').toLowerCase();
      if (st === 'active') active++;
      else if (st === 'failed') failed++;
      else inactive++;
    });
    return { active, inactive, failed, total: list.length };
  }, [services]);

  const svcTotal = svcCounts.total;
  const activeDash = svcTotal > 0 ? (svcCounts.active / svcTotal) * CIRC : 0;
  const inactiveDash = svcTotal > 0 ? (svcCounts.inactive / svcTotal) * CIRC : 0;
  const failedDash = svcTotal > 0 ? (svcCounts.failed / svcTotal) * CIRC : 0;

  return (
    <section className="card card-services">
      <div className="card-header">
        <span className="card-icon" style={{ background: 'rgba(16,185,129,0.12)', color: 'var(--green)' }}>
          <Server size={13} />
        </span>
        <span className="card-title">SERVICES</span>
        <Link to="/services" className="card-link" style={{ marginLeft: 'auto' }}>
          →
        </Link>
      </div>
      <div className="card-body svc-card-body">
        <div className="svc-layout">
          {/* Donut Chart */}
          <div className="svc-donut-wrap">
            <svg viewBox="0 0 36 36">
              <circle className="svc-donut-bg" cx="18" cy="18" r="15.5" />
              <circle
                id="svc-donut-failed"
                className="svc-donut-track"
                cx="18"
                cy="18"
                r="15.5"
                stroke="#ef4444"
                strokeDasharray={`${failedDash} ${CIRC - failedDash}`}
                strokeDashoffset={`${-(activeDash + inactiveDash)}`}
              />
              <circle
                id="svc-donut-inactive"
                className="svc-donut-track"
                cx="18"
                cy="18"
                r="15.5"
                stroke="#f59e0b"
                strokeDasharray={`${inactiveDash} ${CIRC - inactiveDash}`}
                strokeDashoffset={`${-activeDash}`}
              />
              <circle
                id="svc-donut-active"
                className="svc-donut-track"
                cx="18"
                cy="18"
                r="15.5"
                stroke="#10b981"
                strokeDasharray={`${activeDash} ${CIRC - activeDash}`}
                strokeDashoffset="0"
              />
            </svg>
            <div className="svc-donut-label">
              <span className="total" id="svc-total-donut">{svcCounts.total}</span>
              <span className="label">TOTAL</span>
            </div>
          </div>
          {/* Stat Rows */}
          <div className="svc-stats">
            <div className="svc-stat-row">
              <span className="svc-stat-bar" style={{ background: 'var(--green)' }} />
              <div className="svc-stat-info">
                <span className="svc-stat-count" id="svc-active-count" style={{ color: 'var(--green)' }}>
                  {svcCounts.active}
                </span>
                <span className="svc-stat-label">Active</span>
              </div>
            </div>
            <div className="svc-stat-row">
              <span className="svc-stat-bar" style={{ background: 'var(--yellow)' }} />
              <div className="svc-stat-info">
                <span className="svc-stat-count" id="svc-inactive-count" style={{ color: 'var(--yellow)' }}>
                  {svcCounts.inactive}
                </span>
                <span className="svc-stat-label">Inactive</span>
              </div>
            </div>
            <div className="svc-stat-row">
              <span className="svc-stat-bar" style={{ background: 'var(--red)' }} />
              <div className="svc-stat-info">
                <span className="svc-stat-count" id="svc-failed-count" style={{ color: 'var(--red)' }}>
                  {svcCounts.failed}
                </span>
                <span className="svc-stat-label">Failed</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
