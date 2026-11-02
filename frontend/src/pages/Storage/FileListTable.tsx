import React from 'react';
import {
  CheckSquare, Square, Folder, FileCode, FileImage, FileVideo,
  FileAudio, FileArchive, FileText, Binary, Download, Edit3, Trash2
} from 'lucide-react';
import type { FileItem } from '../../api/types';

export interface FileListTableProps {
  loading: boolean;
  error: string | null;
  items: FileItem[];
  searchQuery: string;
  viewMode: 'list' | 'grid';
  selectedPaths: Set<string>;
  onToggleSelectAll: () => void;
  onToggleSelect: (path: string, e: React.MouseEvent) => void;
  onNavigate: (path: string) => void;
  onPreview: (path: string) => void;
  onRename: (item: FileItem) => void;
  onDelete: (paths: string[]) => void;
  sortBy: 'name' | 'size' | 'modified';
  sortOrder: 'asc' | 'desc';
  onSort: (column: 'name' | 'size' | 'modified') => void;
  onRetry: () => void;
}

const getFileCategoryIcon = (category: string, isDir: boolean) => {
  if (isDir) return <Folder size={18} className="cat-folder" />;
  switch (category) {
    case 'code': return <FileCode size={18} className="cat-code" />;
    case 'image': return <FileImage size={18} className="cat-image" />;
    case 'video': return <FileVideo size={18} className="cat-video" />;
    case 'audio': return <FileAudio size={18} className="cat-audio" />;
    case 'archive': return <FileArchive size={18} className="cat-archive" />;
    case 'document': return <FileText size={18} className="cat-document" />;
    case 'binary': return <Binary size={18} className="cat-binary" />;
    default: return <FileText size={18} className="cat-text" />;
  }
};

export const FileListTable: React.FC<FileListTableProps> = ({
  loading,
  error,
  items,
  searchQuery,
  viewMode,
  selectedPaths,
  onToggleSelectAll,
  onToggleSelect,
  onNavigate,
  onPreview,
  onRename,
  onDelete,
  sortBy,
  sortOrder,
  onSort,
  onRetry,
}) => {
  return (
    <div className="file-content-scroll">
      {loading ? (
        <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
          Loading folder contents…
        </div>
      ) : error ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#f87171' }}>
          <p style={{ margin: '0 0 12px', fontWeight: 600 }}>{error}</p>
          <button className="btn btn-xs btn-secondary" onClick={onRetry}>Retry</button>
        </div>
      ) : items.length === 0 ? (
        <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
          {searchQuery ? `No files matching "${searchQuery}"` : 'This directory is empty.'}
        </div>
      ) : viewMode === 'list' ? (
        <table className="file-table">
          <thead>
            <tr>
              <th className="file-col-select" style={{ width: '36px', textAlign: 'center' }}>
                <button
                  className="btn btn-xs btn-ghost"
                  onClick={onToggleSelectAll}
                  style={{ padding: '2px' }}
                  title="Select All"
                >
                  {selectedPaths.size === items.length && items.length > 0 ? (
                    <CheckSquare size={15} color="var(--purple)" />
                  ) : (
                    <Square size={15} />
                  )}
                </button>
              </th>
              <th className="file-col-name" style={{ cursor: 'pointer' }} onClick={() => onSort('name')}>
                Name {sortBy === 'name' ? (sortOrder === 'asc' ? '▲' : '▼') : ''}
              </th>
              <th className="file-col-size" style={{ cursor: 'pointer', width: '100px' }} onClick={() => onSort('size')}>
                Size {sortBy === 'size' ? (sortOrder === 'asc' ? '▲' : '▼') : ''}
              </th>
              <th className="file-col-perms" style={{ width: '120px' }}>Permissions</th>
              <th className="file-col-owner" style={{ width: '120px' }}>Owner</th>
              <th className="file-col-modified" style={{ cursor: 'pointer', width: '150px' }} onClick={() => onSort('modified')}>
                Modified {sortBy === 'modified' ? (sortOrder === 'asc' ? '▲' : '▼') : ''}
              </th>
              <th className="file-col-actions" style={{ width: '110px', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const isSelected = selectedPaths.has(item.path);
              return (
                <tr
                  key={item.path}
                  className={`file-table-row ${isSelected ? 'selected' : ''}`}
                  onClick={() => {
                    if (item.is_dir) onNavigate(item.path);
                    else onPreview(item.path);
                  }}
                >
                  <td className="file-col-select" style={{ textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
                    <button className="btn btn-xs btn-ghost" onClick={(e) => onToggleSelect(item.path, e)} style={{ padding: '2px' }}>
                      {isSelected ? <CheckSquare size={15} color="var(--purple)" /> : <Square size={15} color="var(--text-muted)" />}
                    </button>
                  </td>
                  <td className="file-col-name">
                    <div className="file-name-cell" title={item.name}>
                      <div className={`file-icon-box cat-${item.category}`}>
                        {getFileCategoryIcon(item.category, item.is_dir)}
                      </div>
                      <div className="file-name-info">
                        <div className="file-name-primary">
                          <span className="file-name-text" style={{ fontWeight: item.is_dir ? 600 : 400 }}>{item.name}</span>
                          {item.is_symlink && (
                            <span className="badge badge-lavender file-symlink-badge" style={{ fontSize: '0.68rem', padding: '1px 4px' }}>
                              symlink
                            </span>
                          )}
                        </div>
                        <div className="file-mobile-meta">
                          <span>{item.size_human}</span>
                          <span className="file-mobile-meta-dot">•</span>
                          <span>{item.modified_human}</span>
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="file-col-size font-mono" style={{ color: 'var(--text-secondary)' }}>{item.size_human}</td>
                  <td className="file-col-perms font-mono" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{item.permissions}</td>
                  <td className="file-col-owner" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{item.owner}:{item.group}</td>
                  <td className="file-col-modified" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{item.modified_human}</td>
                  <td className="file-col-actions" style={{ textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      {item.is_dir ? (
                        <button
                          className="btn btn-xs btn-ghost file-row-action-btn"
                          title="Enter folder"
                          onClick={() => onNavigate(item.path)}
                          style={{ padding: '4px', color: 'var(--purple)' }}
                        >
                          <Folder size={13} />
                        </button>
                      ) : (
                        <a
                          href={`/api/storage/file/raw?path=${encodeURIComponent(item.path)}&download=true`}
                          download
                          className="btn btn-xs btn-ghost file-row-action-btn"
                          title="Download"
                          style={{ padding: '4px' }}
                        >
                          <Download size={13} />
                        </a>
                      )}
                      <button
                        className="btn btn-xs btn-ghost file-row-action-btn"
                        title="Rename"
                        onClick={() => onRename(item)}
                        style={{ padding: '4px' }}
                      >
                        <Edit3 size={13} />
                      </button>
                      <button
                        className="btn btn-xs btn-ghost file-row-action-btn"
                        title="Delete"
                        onClick={() => onDelete([item.path])}
                        style={{ padding: '4px', color: '#f87171' }}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <div className="file-grid-container">
          {items.map((item) => {
            const isSelected = selectedPaths.has(item.path);
            return (
              <div
                key={item.path}
                className={`file-grid-card ${isSelected ? 'selected' : ''}`}
                onClick={() => {
                  if (item.is_dir) onNavigate(item.path);
                  else onPreview(item.path);
                }}
                title={`${item.name} (${item.size_human})`}
              >
                <div style={{ position: 'absolute', top: '6px', left: '6px' }} onClick={(e) => onToggleSelect(item.path, e)}>
                  {isSelected ? <CheckSquare size={15} color="var(--purple)" /> : <Square size={15} color="var(--text-dim)" />}
                </div>
                <div className={`file-grid-icon-box cat-${item.category}`}>
                  {item.is_dir ? <Folder size={32} color="#c4b5fd" /> : getFileCategoryIcon(item.category, false)}
                </div>
                <div className="file-grid-name">{item.name}</div>
                <div className="file-grid-meta">{item.size_human}</div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
