import React from 'react';
import { ChevronDown, ArrowUpDown } from 'lucide-react';
import type { ProcessItem } from '../../api/types';
import { formatMemKb } from '../../utils/formatters';
import { ProcessDetailDrawer, parseCommand } from './ProcessDetailDrawer';

export interface ProcessTableProps {
  processes: ProcessItem[];
  loading: boolean;
  sortBy: 'pid' | 'user' | 'cpu' | 'mem' | 'name';
  sortOrder: 'asc' | 'desc';
  onSort: (column: 'pid' | 'user' | 'cpu' | 'mem' | 'name') => void;
  expandedPid: number | null;
  onToggleExpand: (pid: number) => void;
  onKill: (process: ProcessItem) => void;
  onCopy: (text: string, key: string) => void;
  copiedKey: string | null;
}

export const ProcessTable: React.FC<ProcessTableProps> = ({
  processes,
  loading,
  sortBy,
  sortOrder: _sortOrder,
  onSort,
  expandedPid,
  onToggleExpand,
  onKill,
  onCopy,
  copiedKey,
}) => {
  return (
    <table className="table processes-table">
      <thead>
        <tr>
          <th className="proc-col-pid" style={{ width: '80px', cursor: 'pointer' }} onClick={() => onSort('pid')}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              PID {sortBy === 'pid' && <ArrowUpDown size={11} color="var(--accent)" />}
            </span>
          </th>
          <th className="proc-col-user" style={{ width: '110px', cursor: 'pointer' }} onClick={() => onSort('user')}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              USER {sortBy === 'user' && <ArrowUpDown size={11} color="var(--accent)" />}
            </span>
          </th>
          <th className="proc-col-cpu" style={{ width: '90px', cursor: 'pointer' }} onClick={() => onSort('cpu')}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              CPU {sortBy === 'cpu' && <ArrowUpDown size={11} color="var(--accent)" />}
            </span>
          </th>
          <th className="proc-col-mem" style={{ width: '155px', cursor: 'pointer' }} onClick={() => onSort('mem')}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              MEMORY {sortBy === 'mem' && <ArrowUpDown size={11} color="var(--accent)" />}
            </span>
          </th>
          <th className="proc-col-state" style={{ width: '95px' }}>STATE</th>
          <th className="proc-col-time" style={{ width: '85px' }}>TIME</th>
          <th className="proc-col-cmd" style={{ cursor: 'pointer' }} onClick={() => onSort('name')}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              COMMAND {sortBy === 'name' && <ArrowUpDown size={11} color="var(--accent)" />}
            </span>
          </th>
          <th className="proc-col-action" style={{ width: '95px', textAlign: 'right' }}>ACTION</th>
        </tr>
      </thead>
      <tbody>
        {loading ? (
          <tr>
            <td colSpan={8} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
              Loading process table…
            </td>
          </tr>
        ) : processes.length === 0 ? (
          <tr>
            <td colSpan={8} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
              No matching processes found.
            </td>
          </tr>
        ) : (
          processes.map((p) => {
            // CPU display
            let cpuDisplay = '0.0%';
            if (p.cpu > 0) {
              cpuDisplay = `${p.cpu.toFixed(1)}%`;
            } else if (p.cpu_time) {
              cpuDisplay = `${p.cpu_time}s`;
            }
            const isHighCpu = p.cpu > 40;
            const isWarnCpu = p.cpu > 10;

            // Memory display
            const memFormatted = formatMemKb(p.mem);
            const memPct = p.mem_pct != null ? p.mem_pct : undefined;
            const isHighMem = (memPct && memPct > 15) || p.mem > 500000;
            const isWarnMem = (memPct && memPct > 7) || p.mem > 150000;

            // State display
            let stateIndicator = 'status-inactive';
            let stateText = p.stat || '—';
            if (p.stat) {
              if (p.stat.startsWith('R')) {
                stateIndicator = 'status-active';
                stateText = 'Running';
              } else if (p.stat.startsWith('S') || p.stat.startsWith('I')) {
                stateIndicator = 'status-sleeping';
                stateText = 'Sleep';
              } else if (p.stat.startsWith('D')) {
                stateIndicator = 'status-disk';
                stateText = 'Disk wait';
              } else if (p.stat.startsWith('Z')) {
                stateIndicator = 'status-failed';
                stateText = 'Zombie';
              }
            }

            // Command display
            const { binName, binPath, args } = parseCommand(p.command);
            const isExpanded = expandedPid === p.pid;

            return (
              <React.Fragment key={p.pid}>
                <tr
                  className={`proc-row ${isExpanded ? 'is-expanded' : ''}`}
                  onClick={() => onToggleExpand(p.pid)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      onToggleExpand(p.pid);
                    }
                  }}
                  tabIndex={0}
                  title={`Click to view details for ${p.name || binName} (PID: ${p.pid})`}
                >
                  <td className="proc-col-pid font-mono">
                    <span className="proc-pid-pill">
                      <span className="proc-pid-hash">#</span>{p.pid}
                    </span>
                  </td>
                  <td className="proc-col-user">
                    <span className={`badge ${p.user.toLowerCase() === 'root' ? 'system' : 'user'}`} title={p.user}>
                      {p.user.toUpperCase()}
                    </span>
                  </td>
                  <td className="proc-col-cpu">
                    <span
                      className={`font-mono proc-metric-val ${isHighCpu ? 'crit' : isWarnCpu ? 'warn' : ''}`}
                    >
                      <span className="proc-metric-label">CPU: </span>
                      {cpuDisplay}
                    </span>
                  </td>
                  <td className="proc-col-mem">
                    <div className="proc-mem-group">
                      <span
                        className={`font-mono proc-metric-val ${isHighMem ? 'crit' : isWarnMem ? 'warn' : ''}`}
                      >
                        <span className="proc-metric-label">MEM: </span>
                        {memFormatted}
                      </span>
                      {memPct != null && memPct > 0 && (
                        <span className="proc-mem-pct">
                          ({memPct.toFixed(1)}%)
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="proc-col-state">
                    <div className="proc-state-pill">
                      <span className={`status-indicator ${stateIndicator}`} />
                      <span className="font-mono proc-state-text">
                        {stateText}
                      </span>
                    </div>
                  </td>
                  <td className="proc-col-time">
                    <span className="font-mono proc-time-text">
                      <span className="proc-metric-label">Time: </span>
                      {p.time || '0:00'}
                    </span>
                  </td>
                  <td className="proc-col-cmd" title={p.command}>
                    <div className="proc-cmd-cell">
                      <div className="proc-cmd-primary">
                        <strong className="proc-bin-name font-mono">
                          {p.name || binName}
                        </strong>
                        {binPath && (
                          <span className="proc-bin-path font-mono">
                            ({binPath})
                          </span>
                        )}
                      </div>
                      {args && (
                        <span className="proc-cmd-args font-mono" title={args}>
                          {args}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="proc-col-action">
                    <div className="proc-action-group">
                      <button
                        className="btn btn-xs btn-danger proc-kill-btn"
                        title="Kill Process"
                        onClick={(e) => {
                          e.stopPropagation();
                          onKill(p);
                        }}
                      >
                        Kill
                      </button>
                      <span className={`proc-chevron ${isExpanded ? 'is-open' : ''}`} aria-hidden="true">
                        <ChevronDown size={14} />
                      </span>
                    </div>
                  </td>
                </tr>

                {isExpanded && (
                  <ProcessDetailDrawer
                    process={p}
                    onKill={onKill}
                    onCopy={onCopy}
                    copiedKey={copiedKey}
                  />
                )}
              </React.Fragment>
            );
          })
        )}
      </tbody>
    </table>
  );
};
