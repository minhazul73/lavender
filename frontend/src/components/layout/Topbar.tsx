import React from 'react';
import { UserChip } from './UserChip';
import { Menu } from 'lucide-react';

interface TopbarProps {
  title: string;
  onToggleSidebar?: () => void;
  sseStatus?: 'connected' | 'connecting' | 'disconnected';
}

export const Topbar: React.FC<TopbarProps> = ({
  title,
  onToggleSidebar,
  sseStatus = 'connected',
}) => {
  return (
    <header
      className="topbar"
      style={{
        height: 'var(--topbar-height)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        borderBottom: '1px solid var(--border)',
        background: 'rgba(3, 7, 18, 0.75)',
        backdropFilter: 'blur(12px)',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {onToggleSidebar && (
          <button
            type="button"
            onClick={onToggleSidebar}
            className="btn btn-ghost btn-icon mobile-menu-btn"
            aria-label="Toggle navigation menu"
            style={{ display: 'none' }} // Visible on mobile via CSS
          >
            <Menu size={20} />
          </button>
        )}
        <h2
          className="page-title"
          style={{
            margin: 0,
            fontSize: '1.25rem',
            fontWeight: 600,
            color: 'var(--text-primary)',
          }}
        >
          {title}
        </h2>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* SSE Status Indicator */}
        <div
          id="sse-status"
          className={sseStatus}
          title={`Telemetry Stream: ${sseStatus}`}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.74rem',
            fontWeight: 600,
            padding: '4px 10px',
            borderRadius: 'var(--radius-full)',
            border: '1px solid var(--border)',
            background: 'rgba(0, 0, 0, 0.25)',
          }}
        >
          <span
            className="status-indicator"
            style={{
              width: '7px',
              height: '7px',
              borderRadius: '50%',
              background:
                sseStatus === 'connected'
                  ? 'var(--green)'
                  : sseStatus === 'connecting'
                  ? 'var(--yellow)'
                  : 'var(--red)',
              boxShadow:
                sseStatus === 'connected'
                  ? '0 0 8px var(--green)'
                  : sseStatus === 'connecting'
                  ? '0 0 8px var(--yellow)'
                  : '0 0 8px var(--red)',
            }}
          />
          <span style={{ textTransform: 'capitalize', color: 'var(--text-secondary)' }}>
            {sseStatus === 'connected' ? 'Live' : sseStatus}
          </span>
        </div>

        {/* User Chip */}
        <UserChip />
      </div>
    </header>
  );
};
