import React from 'react';
import { Zap, Leaf, Sliders, Flame, LucideIcon } from 'lucide-react';

export interface CpuGovernorCardProps {
  activeGovernor: string;
  availableGovernors: string[];
  onSelectGovernor: (gov: string) => void;
  applying: boolean;
}

interface GovernorProfileConfig {
  id: string;
  actualGov: string | null;
  title: string;
  desc: string;
  color: string;
  bgAlpha: string;
  iconBg: string;
  activeBadgeClass: string;
  Icon: LucideIcon;
  actionLabel: string;
  isAvailable: boolean;
}

export const CpuGovernorCard: React.FC<CpuGovernorCardProps> = ({
  activeGovernor,
  availableGovernors,
  onSelectGovernor,
  applying,
}) => {
  const isPowersaveAvail = availableGovernors.includes('powersave');
  const isPerfAvail = availableGovernors.includes('performance');
  const balancedGov = availableGovernors.includes('schedutil')
    ? 'schedutil'
    : availableGovernors.includes('ondemand')
    ? 'ondemand'
    : null;

  const profiles: GovernorProfileConfig[] = [
    {
      id: 'powersave',
      actualGov: 'powersave',
      title: 'Power Saver',
      desc: 'Pins CPU to minimum frequency. Drastically cuts power draw, maximizes battery runtimes, and keeps thermals cool.',
      color: 'var(--green)',
      bgAlpha: 'rgba(34, 197, 94, 0.08)',
      iconBg: 'rgba(34, 197, 94, 0.15)',
      activeBadgeClass: 'badge-success',
      Icon: Leaf,
      actionLabel: 'Activate Power Saver',
      isAvailable: isPowersaveAvail,
    },
    {
      id: balancedGov || 'schedutil',
      actualGov: balancedGov,
      title: 'Balanced',
      desc: 'Dynamically clocks frequencies based on CPU task load. High responsiveness under load, conserves power when idle.',
      color: 'var(--purple)',
      bgAlpha: 'rgba(124, 58, 237, 0.08)',
      iconBg: 'rgba(124, 58, 237, 0.15)',
      activeBadgeClass: 'badge-lavender',
      Icon: Sliders,
      actionLabel: 'Activate Balanced',
      isAvailable: Boolean(balancedGov),
    },
    {
      id: 'performance',
      actualGov: 'performance',
      title: 'High Performance',
      desc: 'Locks all cores to maximum clock speed. Eliminates ramp-up latency for compiling, heavy computations, or benchmarks.',
      color: 'var(--yellow)',
      bgAlpha: 'rgba(245, 158, 11, 0.08)',
      iconBg: 'rgba(245, 158, 11, 0.15)',
      activeBadgeClass: 'badge-warning',
      Icon: Flame,
      actionLabel: 'Activate Performance',
      isAvailable: isPerfAvail,
    },
  ];

  return (
    <div className="card">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '8px',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Zap size={20} color="var(--purple)" />
          <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600 }}>
            CPU Frequency Scaling Profiles
          </h3>
        </div>
        <span
          className="badge badge-lavender"
          style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
        >
          Active: {activeGovernor}
        </span>
      </div>
      <p
        style={{
          fontSize: '0.85rem',
          color: 'var(--text-secondary)',
          margin: '0 0 16px 0',
          lineHeight: 1.4,
        }}
      >
        Select a kernel frequency governor to optimize battery endurance, thermal dissipation, or
        peak computing performance.
      </p>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '16px',
        }}
      >
        {profiles.map((p) => {
          const isActive = p.actualGov !== null && activeGovernor === p.actualGov;
          const { Icon } = p;
          return (
            <div
              key={p.id}
              className="card"
              style={{
                padding: '16px',
                border: isActive ? `1px solid ${p.color}` : '1px solid var(--border)',
                background: isActive ? p.bgAlpha : 'rgba(255, 255, 255, 0.01)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '10px',
                  }}
                >
                  <div
                    style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '8px',
                      background: p.iconBg,
                      color: p.color,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Icon size={16} />
                  </div>
                  {isActive ? (
                    <span className={`badge ${p.activeBadgeClass}`}>Active</span>
                  ) : p.isAvailable ? (
                    <span className="badge">Available</span>
                  ) : (
                    <span className="badge" style={{ opacity: 0.5 }}>
                      Unsupported
                    </span>
                  )}
                </div>
                <h4 style={{ margin: '0 0 6px 0', fontSize: '0.95rem', fontWeight: 600 }}>
                  {p.title} <span style={{ color: 'var(--text-muted)' }}>({p.id})</span>
                </h4>
                <p
                  style={{
                    fontSize: '0.8rem',
                    color: 'var(--text-secondary)',
                    lineHeight: 1.4,
                    margin: 0,
                  }}
                >
                  {p.desc}
                </p>
              </div>
              <div style={{ marginTop: '16px' }}>
                <button
                  className={`btn ${isActive ? 'btn-primary' : 'btn-secondary'}`}
                  disabled={!p.isAvailable || isActive || applying}
                  onClick={() => p.actualGov && onSelectGovernor(p.actualGov)}
                  style={{ width: '100%', fontSize: '0.85rem' }}
                >
                  {isActive ? 'Currently Active' : p.isAvailable ? p.actionLabel : 'Not Supported'}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
