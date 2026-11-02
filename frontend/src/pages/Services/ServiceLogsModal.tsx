import React, { useState } from 'react';
import { FileText, RefreshCw, Copy, Check } from 'lucide-react';

export interface ServiceLogsModalProps {
  unit: string;
  logs: string[];
  loading: boolean;
  onClose: () => void;
  onRefresh: () => void;
}

export const ServiceLogsModal: React.FC<ServiceLogsModalProps> = ({
  unit,
  logs,
  loading,
  onClose,
  onRefresh,
}) => {
  const [copiedLogs, setCopiedLogs] = useState(false);

  const handleCopy = () => {
    navigator.clipboard?.writeText(logs.join('\n'));
    setCopiedLogs(true);
    setTimeout(() => setCopiedLogs(false), 1500);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content service-modal-wrap service-logs-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="svc-modal-head">
          <div className="svc-head-left">
            <div className="svc-icon-box">
              <FileText size={20} />
            </div>
            <div className="svc-head-title-wrap">
              <div className="svc-title-row">
                <h3 className="svc-modal-title">Logs: {unit}</h3>
              </div>
              <p className="svc-desc">Recent journalctl log output (last 100 entries)</p>
            </div>
          </div>
          <button
            className="svc-modal-close"
            onClick={onClose}
            title="Close"
          >
            ✕
          </button>
        </div>

        <div className="svc-modal-scroll" style={{ padding: '16px 20px' }}>
          <div className="svc-term-box">
            <div className="svc-term-bar">
              <div className="svc-term-dots">
                <span className="svc-term-dot red" />
                <span className="svc-term-dot yellow" />
                <span className="svc-term-dot green" />
              </div>
              <div className="svc-term-cmd">
                <span>journalctl -u {unit} -n 100</span>
              </div>
              <button
                className="svc-term-copy-btn"
                onClick={handleCopy}
                title="Copy logs"
              >
                {copiedLogs ? <Check size={11} /> : <Copy size={11} />}
                <span>{copiedLogs ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <pre className="svc-term-body" style={{ maxHeight: '420px' }}>
              {loading
                ? 'Fetching journalctl log entries…'
                : logs.length > 0
                ? logs.join('\n')
                : 'No journal entries found for this service.'}
            </pre>
          </div>
        </div>

        <div className="svc-modal-foot">
          <div className="svc-foot-left">
            <button
              className="svc-btn-foot"
              onClick={onRefresh}
              disabled={loading}
            >
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>
          <div className="svc-foot-right">
            <button
              className="svc-btn-foot svc-btn-foot-close"
              onClick={onClose}
            >
              <span>Close</span>
              <kbd className="svc-kbd-hint">Esc</kbd>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

