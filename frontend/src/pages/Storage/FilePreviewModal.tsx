import React, { useState, useEffect, useRef } from 'react';
import { api } from '../../api/client';
import { FilePreviewResponse } from '../../api/types';
import { useToast } from '../../context/ToastContext';
import { useOptionalAuth } from '../../context/AuthContext';
import {
  X,
  Download,
  Copy,
  Check,
  Edit3,
  Save,
  FileCode,
  FileText,
  FileImage,
  FileVideo,
  FileAudio,
  File,
  AlertTriangle,
  ShieldAlert,
} from 'lucide-react';

interface FilePreviewModalProps {
  isOpen: boolean;
  filePath: string | null;
  onClose: () => void;
  onSaveSuccess?: () => void;
}

export const FilePreviewModal: React.FC<FilePreviewModalProps> = ({
  isOpen,
  filePath,
  onClose,
  onSaveSuccess,
}) => {
  const { addToast } = useToast();
  const auth = useOptionalAuth();
  const session = auth?.session;
  const isElevated = Boolean(auth?.isElevated);
  const [data, setData] = useState<FilePreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Edit mode state
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const [wrapLines, setWrapLines] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const canEdit = Boolean(data?.is_text && (data?.is_writable || session?.is_admin || isElevated || session?.can_elevate));

  useEffect(() => {
    if (!isOpen || !filePath) {
      setData(null);
      setIsEditing(false);
      setError(null);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);

    api
      .get<FilePreviewResponse>(`/api/storage/file/view?path=${encodeURIComponent(filePath)}`)
      .then((res) => {
        if (!isMounted) return;
        setData(res);
        setEditContent(res.content || '');
      })
      .catch((err: unknown) => {
        if (!isMounted) return;
        const msg = err instanceof Error ? err.message : 'Failed to inspect file';
        setError(msg);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, filePath]);

  if (!isOpen || !filePath) return null;

  const handleCopyContent = async () => {
    const textToCopy = isEditing ? editContent : data?.content || '';
    if (!textToCopy) return;
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      addToast('File content copied to clipboard', 'info');
    } catch {
      addToast('Failed to copy to clipboard', 'error');
    }
  };

  const handleSave = async () => {
    if (!filePath) return;
    setSaving(true);
    try {
      await api.post('/api/storage/file/save', {
        path: filePath,
        content: editContent,
      });
      addToast('File saved successfully', 'success');
      setIsEditing(false);
      if (data) {
        setData({
          ...data,
          content: editContent,
          size: new Blob([editContent]).size,
          line_count: editContent.split('\n').length,
        });
      }
      onSaveSuccess?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to save changes';
      addToast(msg, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      handleSave();
    } else if (e.key === 'Tab') {
      e.preventDefault();
      const textarea = e.currentTarget;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const val = textarea.value;
      setEditContent(val.substring(0, start) + '  ' + val.substring(end));
      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.selectionStart = textareaRef.current.selectionEnd = start + 2;
        }
      }, 0);
    }
  };

  const rawUrl = `/api/storage/file/raw?path=${encodeURIComponent(filePath)}`;
  const downloadUrl = `/api/storage/file/raw?path=${encodeURIComponent(filePath)}&download=true`;

  const category = data?.category || 'text';

  const renderIcon = () => {
    switch (category) {
      case 'code':
        return <FileCode size={20} color="#34d399" />;
      case 'image':
        return <FileImage size={20} color="#f472b6" />;
      case 'video':
        return <FileVideo size={20} color="#c084fc" />;
      case 'audio':
        return <FileAudio size={20} color="#fbbf24" />;
      default:
        return <FileText size={20} color="#a78bfa" />;
    }
  };

  return (
    <div
      className="preview-modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="preview-modal-dialog" role="dialog" aria-modal="true">
        {/* Header */}
        <div className="preview-modal-header">
          <div className="preview-modal-title-group" style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
            {renderIcon()}
            <div style={{ minWidth: 0 }}>
              <h3
                style={{
                  margin: 0,
                  fontSize: '1rem',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  maxWidth: '420px',
                }}
                title={data?.name || filePath}
              >
                {data?.name || filePath.split('/').pop()}
              </h3>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {data?.size_human || '—'} · {data?.permissions || ''} · {filePath}
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="preview-modal-actions" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {data?.is_text && (
              <>
                <button
                  className="btn btn-xs btn-secondary"
                  onClick={() => setWrapLines(!wrapLines)}
                  title="Toggle Word Wrap"
                >
                  {wrapLines ? 'Unwrap' : 'Wrap'}
                </button>

                <button
                  className="btn btn-xs btn-secondary"
                  onClick={handleCopyContent}
                  title="Copy file content"
                >
                  {copied ? <Check size={14} color="var(--green)" /> : <Copy size={14} />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>

                {canEdit && (
                  <button
                    className={`btn btn-xs ${isEditing ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => {
                      if (isEditing) {
                        handleSave();
                      } else {
                        setIsEditing(true);
                      }
                    }}
                    disabled={saving}
                  >
                    {isEditing ? (
                      <>
                        <Save size={14} />
                        <span>{saving ? 'Saving…' : 'Save'}</span>
                      </>
                    ) : (
                      <>
                        <Edit3 size={14} />
                        <span>Edit</span>
                      </>
                    )}
                  </button>
                )}

                {isEditing && (
                  <button
                    className="btn btn-xs btn-ghost"
                    onClick={() => {
                      setEditContent(data.content || '');
                      setIsEditing(false);
                    }}
                    disabled={saving}
                  >
                    Cancel
                  </button>
                )}
              </>
            )}

            <a
              href={downloadUrl}
              download
              className="btn btn-xs btn-secondary"
              style={{ textDecoration: 'none' }}
              title="Download file"
            >
              <Download size={14} />
              <span>Download</span>
            </a>

            <button
              className="btn btn-xs btn-ghost"
              onClick={onClose}
              title="Close modal"
              style={{ padding: '6px' }}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="preview-modal-body">
          {loading ? (
            <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
              Loading file preview…
            </div>
          ) : error ? (
            <div
              style={{
                padding: '40px',
                textAlign: 'center',
                color: '#f87171',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '12px',
              }}
            >
              <AlertTriangle size={36} />
              <div>{error}</div>
            </div>
          ) : data?.category === 'image' ? (
            <div className="image-preview-frame">
              <img src={rawUrl} alt={data.name} />
            </div>
          ) : data?.category === 'video' ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '16px' }}>
              <video
                controls
                src={rawUrl}
                style={{
                  maxWidth: '100%',
                  maxHeight: '480px',
                  borderRadius: 'var(--radius-md)',
                  background: '#000',
                }}
              />
            </div>
          ) : data?.category === 'audio' ? (
            <div style={{ padding: '40px', textAlign: 'center' }}>
              <audio controls src={rawUrl} style={{ width: '100%', maxWidth: '500px' }} />
            </div>
          ) : data?.is_text ? (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '8px' }}>
              {data.truncated && (
                <div
                  style={{
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    background: 'rgba(245, 158, 11, 0.15)',
                    border: '1px solid rgba(245, 158, 11, 0.3)',
                    color: '#fbbf24',
                    fontSize: '0.8rem',
                  }}
                >
                  Large file preview is truncated to 2 MB. Download file to view full contents.
                </div>
              )}

              {isEditing ? (
                <>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      fontSize: '0.74rem',
                      color: 'var(--text-muted)',
                      padding: '0 2px',
                    }}
                  >
                    <span>
                      Shortcuts: <strong>Ctrl+S</strong> to save · <strong>Tab</strong> to indent
                    </span>
                    {(!data.is_writable || session?.is_admin || isElevated) && (
                      <span
                        className="badge badge-lavender"
                        style={{
                          fontSize: '0.68rem',
                          padding: '1px 6px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        <ShieldAlert size={11} />
                        Elevated / Sudo Edit
                      </span>
                    )}
                  </div>
                  <textarea
                    ref={textareaRef}
                    className="code-editor-area"
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    onKeyDown={handleKeyDown}
                    style={{
                      flex: 1,
                      minHeight: '420px',
                      whiteSpace: wrapLines ? 'pre-wrap' : 'pre',
                    }}
                    autoFocus
                    placeholder="File content..."
                    spellCheck={false}
                  />
                </>
              ) : (
                <pre
                  style={{
                    margin: 0,
                    padding: '16px',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(5, 12, 24, 0.85)',
                    border: '1px solid var(--border-subtle)',
                    color: '#f1f5f9',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.84rem',
                    lineHeight: '1.6',
                    overflowX: 'auto',
                    whiteSpace: wrapLines ? 'pre-wrap' : 'pre',
                    wordBreak: wrapLines ? 'break-all' : 'normal',
                    minHeight: '380px',
                  }}
                >
                  {data.content || '(Empty file)'}
                </pre>
              )}
            </div>
          ) : (
            <div
              style={{
                padding: '60px',
                textAlign: 'center',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '16px',
              }}
            >
              <File size={52} color="var(--purple)" />
              <div>
                <h4 style={{ margin: '0 0 6px', fontSize: '1.1rem' }}>{data?.name}</h4>
                <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  Binary or non-text file ({data?.size_human})
                </p>
              </div>
              <a href={downloadUrl} download className="btn btn-primary" style={{ textDecoration: 'none' }}>
                <Download size={16} />
                <span>Download File</span>
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
