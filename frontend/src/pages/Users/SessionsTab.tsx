import React from 'react';
import type { UserSessionItem, LoginHistoryItem } from '../../api/types';
import { Terminal, XCircle, Clock } from 'lucide-react';

export interface SessionsTabProps {
  activeSessions: UserSessionItem[];
  loginHistory: LoginHistoryItem[];
  onTerminateSession: (session: UserSessionItem) => void;
}

export const SessionsTab: React.FC<SessionsTabProps> = ({
  activeSessions,
  loginHistory,
  onTerminateSession,
}) => {
  return (
    <div className="users-sessions-container">
      {/* Active Terminal & Remote Logins */}
      <div className="card users-sessions-card">
        <div className="card-header sessions-card-header">
          <div className="sessions-header-titles">
            <h3 className="sessions-card-title">Active Terminal & Remote Logins</h3>
            <span className="sessions-card-subtitle">
              Real-time logged-in TTYs & SSH sessions
            </span>
          </div>
          <span className="badge badge-lavender sessions-online-badge">{activeSessions.length} Online</span>
        </div>

        <div className="card-body sessions-card-body" style={{ padding: 0 }}>
          <div className="sessions-table-wrap">
            <table className="table sessions-table active-sessions-table">
              <thead>
                <tr>
                  <th className="col-status" style={{ width: '40px' }}>Status</th>
                  <th className="col-user">User</th>
                  <th className="col-tty">Terminal (TTY)</th>
                  <th className="col-host">Remote Host / IP</th>
                  <th className="col-login">Login Time</th>
                  <th className="col-idle">Idle Duration</th>
                  <th className="col-actions" style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {activeSessions.length === 0 ? (
                  <tr className="sessions-empty-row">
                    <td colSpan={7} className="sessions-empty-cell">
                      <div className="sessions-empty-content">
                        <Terminal size={22} className="sessions-empty-icon" />
                        <span>No active terminal or SSH sessions connected</span>
                      </div>
                    </td>
                  </tr>
                ) : (
                  activeSessions.map((s) => (
                    <tr key={s.tty} className="session-item-row">
                      <td className="session-cell-status">
                        <span className="session-beacon" title="Session Active" />
                      </td>
                      <td className="session-cell-user">
                        <div className="session-user-wrap">
                          <strong className="session-username">{s.user}</strong>
                        </div>
                      </td>
                      <td className="session-cell-tty font-mono">
                        <span className="session-tty-badge">{s.tty}</span>
                      </td>
                      <td className="session-cell-host font-mono">
                        <span className="sessions-meta-label">Host: </span>
                        <span className="sessions-meta-val">{s.from || s.host || 'local'}</span>
                      </td>
                      <td className="session-cell-login">
                        <span className="sessions-meta-label">Login: </span>
                        <span className="sessions-meta-val">{s.login_time || '—'}</span>
                      </td>
                      <td className="session-cell-idle font-mono">
                        <span className="sessions-meta-label">Idle: </span>
                        <span className="sessions-meta-val">{s.idle || '0s'}</span>
                      </td>
                      <td className="session-cell-actions">
                        <button
                          className="btn btn-xs btn-danger session-disconnect-btn"
                          onClick={() => onTerminateSession(s)}
                          title={`Terminate session on ${s.tty}`}
                        >
                          <XCircle size={13} />
                          <span>Disconnect</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Recent Login History (lastlog/wtmp) */}
      <div className="card users-sessions-card">
        <div className="card-header sessions-card-header">
          <div className="sessions-header-titles">
            <h3 className="sessions-card-title">Recent Login History</h3>
            <span className="sessions-card-subtitle">
              Last 10 system authentication sessions (from lastlog/wtmp)
            </span>
          </div>
        </div>

        <div className="card-body sessions-card-body" style={{ padding: 0 }}>
          <div className="sessions-table-wrap">
            <table className="table sessions-table history-sessions-table">
              <thead>
                <tr>
                  <th className="hist-col-user">User</th>
                  <th className="hist-col-tty">Terminal</th>
                  <th className="hist-col-host">Host</th>
                  <th className="hist-col-time">Time / Session Duration</th>
                </tr>
              </thead>
              <tbody>
                {loginHistory.length === 0 ? (
                  <tr className="sessions-empty-row">
                    <td colSpan={4} className="sessions-empty-cell">
                      <div className="sessions-empty-content">
                        <Clock size={20} className="sessions-empty-icon" />
                        <span>No recent logins recorded</span>
                      </div>
                    </td>
                  </tr>
                ) : (
                  loginHistory.map((h, idx) => (
                    <tr key={idx} className="history-item-row">
                      <td className="hist-cell-user font-mono">
                        <span className="hist-username">{h.user}</span>
                      </td>
                      <td className="hist-cell-tty font-mono">
                        <span className="hist-tty-badge">{h.tty}</span>
                      </td>
                      <td className="hist-cell-host font-mono">
                        <span className="hist-host-badge">{h.host || 'local'}</span>
                      </td>
                      <td className="hist-cell-time">
                        <span className="hist-time-val">{h.time}</span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
