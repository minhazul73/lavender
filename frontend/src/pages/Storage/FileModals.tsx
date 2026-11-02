import React, { useState, useEffect } from 'react';
import { X, FolderPlus, FilePlus, Edit3 } from 'lucide-react';


interface CreateFolderModalProps {
  isOpen: boolean;
  parentPath: string;
  onClose: () => void;
  onSubmit: (name: string) => Promise<void>;
  loading: boolean;
}

export const CreateFolderModal: React.FC<CreateFolderModalProps> = ({
  isOpen,
  parentPath,
  onClose,
  onSubmit,
  loading,
}) => {
  const [name, setName] = useState('');

  useEffect(() => {
    if (isOpen) setName('');
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onSubmit(name.trim());
  };

  return (
    <div className="preview-modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div
        className="card"
        style={{ width: '100%', maxWidth: '440px', padding: '24px', background: 'var(--bg-primary)' }}
        role="dialog"
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FolderPlus size={20} color="var(--purple)" />
            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>Create New Folder</h3>
          </div>
          <button className="btn btn-xs btn-ghost" onClick={onClose} disabled={loading}>
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '12px' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
              Directory Name
            </label>
            <input
              type="text"
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. projects, notes, backup"
              autoFocus
              required
              disabled={loading}
              style={{ width: '100%' }}
            />
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '20px' }}>
            Location: <code className="font-mono">{parentPath}</code>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading || !name.trim()}>
              {loading ? 'Creating…' : 'Create Folder'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

interface CreateFileModalProps {
  isOpen: boolean;
  parentPath: string;
  onClose: () => void;
  onSubmit: (name: string, content: string) => Promise<void>;
  loading: boolean;
}

export const CreateFileModal: React.FC<CreateFileModalProps> = ({
  isOpen,
  parentPath,
  onClose,
  onSubmit,
  loading,
}) => {
  const [name, setName] = useState('');
  const [content, setContent] = useState('');

  useEffect(() => {
    if (isOpen) {
      setName('');
      setContent('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onSubmit(name.trim(), content);
  };

  return (
    <div className="preview-modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div
        className="card"
        style={{ width: '100%', maxWidth: '520px', padding: '24px', background: 'var(--bg-primary)' }}
        role="dialog"
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FilePlus size={20} color="var(--accent)" />
            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>Create New File</h3>
          </div>
          <button className="btn btn-xs btn-ghost" onClick={onClose} disabled={loading}>
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '12px' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
              File Name (with extension)
            </label>
            <input
              type="text"
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. script.sh, index.html, notes.txt"
              autoFocus
              required
              disabled={loading}
              style={{ width: '100%' }}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
              Initial Content (optional)
            </label>
            <textarea
              className="code-editor-area"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="# Initial file content..."
              disabled={loading}
              style={{ minHeight: '120px', maxHeight: '240px' }}
            />
          </div>

          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '20px' }}>
            Location: <code className="font-mono">{parentPath}</code>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading || !name.trim()}>
              {loading ? 'Creating…' : 'Create File'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

interface RenameModalProps {
  isOpen: boolean;
  currentPath: string;
  currentName: string;
  onClose: () => void;
  onSubmit: (newName: string) => Promise<void>;
  loading: boolean;
}

export const RenameModal: React.FC<RenameModalProps> = ({
  isOpen,
  currentPath,
  currentName,
  onClose,
  onSubmit,
  loading,
}) => {
  const [newName, setNewName] = useState(currentName);

  useEffect(() => {
    if (isOpen) setNewName(currentName);
  }, [isOpen, currentName]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim() || newName.trim() === currentName) return;
    onSubmit(newName.trim());
  };

  return (
    <div className="preview-modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div
        className="card"
        style={{ width: '100%', maxWidth: '440px', padding: '24px', background: 'var(--bg-primary)' }}
        role="dialog"
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Edit3 size={20} color="var(--purple)" />
            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>Rename Item</h3>
          </div>
          <button className="btn btn-xs btn-ghost" onClick={onClose} disabled={loading}>
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '12px' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
              New Name
            </label>
            <input
              type="text"
              className="input"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              autoFocus
              required
              disabled={loading}
              style={{ width: '100%' }}
            />
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '20px' }}>
            Target: <code className="font-mono">{currentPath}</code>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || !newName.trim() || newName.trim() === currentName}
            >
              {loading ? 'Renaming…' : 'Rename'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
