import React from 'react';
import { Terminal, Copy, Check } from 'lucide-react';
import type { ProcessItem } from '../../api/types';
import { formatMemKb } from '../../utils/formatters';

export function parseCommand(cmd: string | undefined): { binName: string; binPath: string; args: string } {
  if (!cmd) return { binName: '—', binPath: '', args: '' };
  const trimmed = cmd.trim();
  if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
    return { binName: trimmed, binPath: '', args: '' };
  }
  const firstSpace = trimmed.indexOf(' ');
  let exe = trimmed;
  let args = '';
  if (firstSpace !== -1) {
    exe = trimmed.substring(0, firstSpace);
    args = trimmed.substring(firstSpace + 1);
  }
  const slashIdx = exe.lastIndexOf('/');
  const binName = slashIdx !== -1 ? exe.substring(slashIdx + 1) : exe;
  const binPath = slashIdx !== -1 ? exe.substring(0, slashIdx + 1) : '';
  return { binName, binPath, args };
}

export interface ProcessDetailDrawerProps {
  process: ProcessItem;
  onKill: (process: ProcessItem) => void;
  onCopy: (text: string, key: string) => void;
  copiedKey: string | null;
}

export const ProcessDetailDrawer: React.FC<ProcessDetailDrawerProps> = ({
  process: p,
  onKill,
  onCopy,
  copiedKey,
}) => {
  let cpuDisplay = '0.0%';
  if (p.cpu > 0) {
    cpuDisplay = `${p.cpu.toFixed(1)}%`;
  } else if (p.cpu_time) {
    cpuDisplay = `${p.cpu_time}s`;
  }
  const isHighCpu = p.cpu > 40;
  const isWarnCpu = p.cpu > 10;

  const memFormatted = formatMemKb(p.mem);
  const memPct = p.mem_pct != null ? p.mem_pct : undefined;

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

  const { binName, binPath } = parseCommand(p.command);

  return (
    <tr className="proc-drawer-row">
      <td colSpan={8} className="proc-drawer-cell">
        <div className="proc-drawer-content">
          <div className="proc-drawer-header">
            <div className="proc-drawer-title">
              <Terminal size={14} />
              <span>Command Details</span>
            </div>
            <div className="proc-drawer-actions">
              <button
                type="button"
                className="btn btn-xs btn-secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  onCopy(p.command || '', `cmd-${p.pid}`);
                }}
              >
                {copiedKey === `cmd-${p.pid}` ? <Check size={12} color="var(--green)" /> : <Copy size={12} />}
                <span>{copiedKey === `cmd-${p.pid}` ? 'Copied' : 'Copy Command'}</span>
              </button>
              <button
                type="button"
                className="btn btn-xs btn-secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  onCopy(String(p.pid), `pid-${p.pid}`);
                }}
              >
                {copiedKey === `pid-${p.pid}` ? <Check size={12} color="var(--green)" /> : <Copy size={12} />}
                <span>{copiedKey === `pid-${p.pid}` ? 'Copied' : 'Copy PID'}</span>
              </button>
            </div>
          </div>

          {/* Full Command Box */}
          <div className="proc-command-box font-mono">
            {p.command}
          </div>

          {/* Detailed Context Specs */}
          <div className="proc-drawer-specs">
            <div className="proc-spec-item">
              <span className="proc-spec-label">PID</span>
              <span className="proc-spec-val font-mono">{p.pid}</span>
            </div>
            <div className="proc-spec-item">
              <span className="proc-spec-label">USER</span>
              <span className="proc-spec-val">{p.user}</span>
            </div>
            <div className="proc-spec-item">
              <span className="proc-spec-label">STATUS</span>
              <span className="proc-spec-val" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span className={`status-indicator ${stateIndicator}`} />
                {stateText} {p.stat ? `(${p.stat})` : ''}
              </span>
            </div>
            <div className="proc-spec-item">
              <span className="proc-spec-label">CPU TIME</span>
              <span className="proc-spec-val font-mono">{p.time || '0:00'}</span>
            </div>
            <div className="proc-spec-item">
              <span className="proc-spec-label">CPU USAGE</span>
              <span className="proc-spec-val font-mono" style={{ color: isHighCpu ? 'var(--red)' : isWarnCpu ? 'var(--yellow)' : 'inherit' }}>
                {cpuDisplay}
              </span>
            </div>
            <div className="proc-spec-item">
              <span className="proc-spec-label">MEMORY</span>
              <span className="proc-spec-val font-mono">
                {memFormatted} {memPct != null && memPct > 0 ? `(${memPct.toFixed(1)}%)` : ''}
              </span>
            </div>
            {binPath && (
              <div className="proc-spec-item proc-spec-full">
                <span className="proc-spec-label">EXECUTABLE PATH</span>
                <span className="proc-spec-val font-mono" style={{ wordBreak: 'break-all' }}>{binPath}{binName}</span>
              </div>
            )}
          </div>

          {/* Drawer Footer Action */}
          <div className="proc-drawer-footer">
            <button
              type="button"
              className="btn btn-sm btn-danger proc-drawer-kill-btn"
              onClick={(e) => {
                e.stopPropagation();
                onKill(p);
              }}
            >
              Terminate Process (SIGKILL)
            </button>
          </div>
        </div>
      </td>
    </tr>
  );
};

