import React, { useState } from 'react';
import {
  Server, Activity, Cpu, Layers, RotateCw, Square, Play, FileText, Copy, Check
} from 'lucide-react';

export interface ServiceDetailData {
  name: string;
  user: boolean;
  output: string;
  error?: string;
  active: boolean;
  active_state: string;
  sub_state: string;
  description: string;
  unit_file_state: string;
  since: string;
  tasks: string;
  main_pid: number | null;
  process_name: string;
  memory: string;
  cpu: string;
  docs: string;
}

export interface ServiceDetailModalProps {
  service: { name: string; isUser: boolean };
  detail: ServiceDetailData | null;
  loading: boolean;
  onClose: () => void;
  onAction: (action: 'start' | 'stop' | 'restart') => void;
  onViewLogs: (unit: string) => void;
}

export const ServiceDetailModal: React.FC<ServiceDetailModalProps> = ({
  service,
  detail,
  loading,
  onClose,
  onAction,
  onViewLogs,
}) => {
  const [copiedName, setCopiedName] = useState(false);
  const [copiedTerm, setCopiedTerm] = useState(false);

  const copyToClipboard = (text: string, type: 'name' | 'term') => {
    navigator.clipboard?.writeText(text);
    if (type === 'name') {
      setCopiedName(true);
      setTimeout(() => setCopiedName(false), 1500);
    } else if (type === 'term') {
      setCopiedTerm(true);
      setTimeout(() => setCopiedTerm(false), 1500);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content service-modal-wrap" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="svc-modal-head">
          <div className="svc-head-left">
            <div className="svc-icon-box">
              <Server size={22} />
            </div>
            <div className="svc-head-title-wrap">
              <div className="svc-title-row">
                <h3 className="svc-modal-title">{service.name}</h3>
                <button
                  className={`svc-copy-chip ${copiedName ? 'copied' : ''}`}
                  onClick={() => copyToClipboard(service.name, 'name')}
                  title="Copy service name"
                >
                  {copiedName ? <Check size={11} /> : <Copy size={11} />}
                </button>
                <span className={`svc-badge-pill ${service.isUser ? 'svc-badge-user' : 'svc-badge-system'}`}>
                  {service.isUser ? 'User Service' : 'System Service'}
                </span>
                {detail?.unit_file_state && (
                  <span className={`svc-badge-pill svc-badge-${detail.unit_file_state.toLowerCase()}`}>
                    {detail.unit_file_state.toLowerCase()}
                  </span>
                )}
              </div>
              <p className="svc-desc">
                {detail?.description || `Systemd ${service.isUser ? 'User' : 'System'} Unit`}
              </p>
            </div>
          </div>
          <button className="svc-modal-close" onClick={onClose} title="Close">✕</button>
        </div>

        {/* Scrollable Body */}
        <div className="svc-modal-scroll">
          {loading ? (
            <div style={{ padding: '60px 24px', textAlign: 'center', color: 'var(--text-muted)' }}>
              Inspecting <strong>{service.name}</strong>…
            </div>
          ) : detail ? (
            <>
              {/* 4 Metrics Grid */}
              <div className="svc-metrics-grid">
                {/* State Card */}
                <div className="svc-metric-card">
                  <div className="svc-metric-top">
                    <span>STATE</span>
                    <Activity size={14} className="svc-metric-icon" />
                  </div>
                  <div className="svc-metric-val">
                    <span className={`svc-state-pill ${detail.active ? 'active' : detail.active_state === 'failed' ? 'failed' : 'inactive'}`}>
                      <span className={`svc-dot ${detail.active ? 'active' : detail.active_state === 'failed' ? 'failed' : 'inactive'}`} />
                      {detail.active_state
                        ? detail.active_state.charAt(0).toUpperCase() + detail.active_state.slice(1)
                        : detail.active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div className="svc-metric-sub">
                    {detail.since
                      ? detail.since.split(';')[1]?.trim() || detail.since
                      : detail.active ? 'Operational' : 'Not running'}
                  </div>
                </div>

                {/* Main PID Card */}
                <div className="svc-metric-card">
                  <div className="svc-metric-top">
                    <span>MAIN PID</span>
                    <Cpu size={14} className="svc-metric-icon" />
                  </div>
                  <div className="svc-metric-val mono">
                    {detail.main_pid ? `#${detail.main_pid}` : '—'}
                  </div>
                  <div className="svc-metric-sub">
                    {detail.process_name || (detail.main_pid ? 'Main process' : 'Not running')}
                  </div>
                </div>

                {/* Memory Card */}
                <div className="svc-metric-card">
                  <div className="svc-metric-top">
                    <span>MEMORY</span>
                    <Layers size={14} className="svc-metric-icon" />
                  </div>
                  <div className="svc-metric-val mono">
                    {detail.memory ? detail.memory.split('(')[0]?.trim() : '—'}
                  </div>
                  <div className="svc-metric-sub">
                    {detail.memory ? 'Resident memory' : 'No allocation'}
                  </div>
                </div>

                {/* CPU / Tasks Card */}
                <div className="svc-metric-card">
                  <div className="svc-metric-top">
                    <span>CPU / TASKS</span>
                    <Activity size={14} className="svc-metric-icon" />
                  </div>
                  <div className="svc-metric-val mono">
                    {detail.cpu || '—'}
                  </div>
                  <div className="svc-metric-sub">
                    {detail.tasks ? `${detail.tasks} tasks active` : 'Accumulated'}
                  </div>
                </div>
              </div>

              {/* Terminal Status Output */}
              <div className="svc-term-wrap">
                <div className="svc-term-box">
                  <div className="svc-term-bar">
                    <div className="svc-term-dots">
                      <span className="svc-term-dot red" />
                      <span className="svc-term-dot yellow" />
                      <span className="svc-term-dot green" />
                    </div>
                    <div className="svc-term-cmd">
                      <span>systemctl status {service.name}</span>
                    </div>
                    <button
                      className="svc-term-copy-btn"
                      onClick={() => copyToClipboard(detail.output || '', 'term')}
                      title="Copy terminal output"
                    >
                      {copiedTerm ? <Check size={11} /> : <Copy size={11} />}
                      <span>{copiedTerm ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                  <pre className="svc-term-body">{detail.output || 'No output available.'}</pre>
                </div>
              </div>
            </>
          ) : (
            <div style={{ padding: '40px 24px', textAlign: 'center', color: 'var(--text-muted)' }}>
              Failed to load service details.
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="svc-modal-foot">
          <div className="svc-foot-left">
            {detail?.active ? (
              <>
                <button
                  className="svc-btn-foot"
                  title="Restart Service"
                  style={{ color: '#c4b5fd', borderColor: 'rgba(139, 92, 246, 0.4)' }}
                  onClick={() => onAction('restart')}
                >
                  <RotateCw size={13} />
                  <span>Restart</span>
                </button>
                <button
                  className="svc-btn-foot"
                  title="Stop Service"
                  style={{ color: '#f87171', borderColor: 'rgba(239, 68, 68, 0.4)' }}
                  onClick={() => onAction('stop')}
                >
                  <Square size={13} />
                  <span>Stop</span>
                </button>
              </>
            ) : (
              <button
                className="svc-btn-foot"
                title="Start Service"
                style={{ color: '#34d399', borderColor: 'rgba(16, 185, 129, 0.4)' }}
                onClick={() => onAction('start')}
              >
                <Play size={13} />
                <span>Start</span>
              </button>
            )}
            <button className="svc-btn-foot" onClick={() => onViewLogs(service.name)}>
              <FileText size={13} />
              <span>View Logs</span>
            </button>
          </div>
          <div className="svc-foot-right">
            <button className="svc-btn-foot svc-btn-foot-close" onClick={onClose}>
              <span>Close</span>
              <kbd className="svc-kbd-hint">Esc</kbd>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
