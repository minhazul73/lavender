import React from 'react';
import { Link } from 'react-router-dom';
import { FileText } from 'lucide-react';
import { formatLogTime } from '../../utils/formatters';

export interface LogsCardProps {
  recentLogs: Array<any>;
}

export const LogsCard: React.FC<LogsCardProps> = ({ recentLogs }) => {
  return (
    <section className="card card-logs">
      <div className="card-header">
        <span className="card-icon" style={{ background: 'rgba(6,182,212,0.12)', color: 'var(--accent)' }}>
          <FileText size={13} />
        </span>
        <span className="card-title">RECENT LOGS</span>
        <Link to="/services" className="card-link" style={{ marginLeft: 'auto' }}>
          All →
        </Link>
      </div>
      <div className="card-body logs-card-body" style={{ padding: 0 }}>
        <div id="recent-logs" className="recent-logs-list">
          {recentLogs.length > 0 ? (
            recentLogs.map((log, idx) => {
              const timestamp = typeof log === 'object' && log !== null ? log.timestamp : '';
              const service = typeof log === 'object' && log !== null ? log.service : '';
              const message = typeof log === 'object' && log !== null ? log.message || '' : String(log);
              const level = typeof log === 'object' && log !== null ? log.level : 'info';
              const dotColor = level === 'error' ? 'var(--red)' : level === 'warning' ? 'var(--yellow)' : 'var(--green)';
              const { time: timeDisplay, full: timeTooltip } = formatLogTime(timestamp);

              return (
                <div key={idx} className="log-entry">
                  <span className="log-time" title={timeTooltip || undefined}>
                    {timeDisplay}
                  </span>
                  <span className="log-dot" style={{ background: dotColor }} />
                  <span className="log-msg">
                    {service ? `${service}: ` : ''}{message}
                  </span>
                </div>
              );
            })
          ) : (
            <div className="log-entry">
              <span className="log-time">—</span>
              <span className="log-dot" style={{ background: 'var(--text-muted)' }} />
              <span className="log-msg">Loading logs…</span>
            </div>
          )}
        </div>
      </div>
    </section>
  );
};

