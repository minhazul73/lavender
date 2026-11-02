import React from 'react';
import {
  Search, X, Eye, EyeOff, List, Grid, FolderPlus, FilePlus, Upload, Trash2
} from 'lucide-react';

export interface FileToolbarProps {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  showHidden: boolean;
  setShowHidden: (show: boolean) => void;
  viewMode: 'list' | 'grid';
  setViewMode: (mode: 'list' | 'grid') => void;
  canWrite: boolean;
  onNewFolder: () => void;
  onNewFile: () => void;
  onUploadClick: () => void;
  uploading: boolean;
  selectedCount: number;
  onDeleteSelected: () => void;
}

export const FileToolbar: React.FC<FileToolbarProps> = ({
  searchQuery,
  setSearchQuery,
  showHidden,
  setShowHidden,
  viewMode,
  setViewMode,
  canWrite,
  onNewFolder,
  onNewFile,
  onUploadClick,
  uploading,
  selectedCount,
  onDeleteSelected,
}) => {
  return (
    <div className="file-toolbar">
      <div className="file-toolbar-left">
        <div className="file-search-box">
          <Search size={14} style={{ position: 'absolute', left: '10px', color: 'var(--text-muted)' }} />
          <input
            type="text"
            className="file-search-input"
            placeholder="Filter files in directory…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button
              type="button"
              className="btn btn-xs btn-ghost"
              onClick={() => setSearchQuery('')}
              style={{ position: 'absolute', right: '4px', padding: '2px', color: 'var(--text-muted)' }}
              title="Clear filter"
            >
              <X size={12} />
            </button>
          )}
        </div>

        <div className="file-toolbar-controls">
          <button
            className={`btn btn-xs ${showHidden ? 'btn-primary' : 'btn-secondary'} file-hidden-btn`}
            onClick={() => setShowHidden(!showHidden)}
            title="Toggle hidden dotfiles"
          >
            {showHidden ? <Eye size={14} /> : <EyeOff size={14} />}
            <span>Hidden</span>
          </button>

          <div className="file-view-toggle">
            <button
              className={`file-view-toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
              onClick={() => setViewMode('list')}
              title="List View"
            >
              <List size={15} />
            </button>
            <button
              className={`file-view-toggle-btn ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
              title="Grid View"
            >
              <Grid size={15} />
            </button>
          </div>
        </div>
      </div>

      <div className="file-toolbar-right">
        {canWrite && (
          <div className="file-toolbar-actions">
            <button
              className="btn btn-xs btn-secondary"
              onClick={onNewFolder}
              title="New Folder"
            >
              <FolderPlus size={14} color="var(--purple)" />
              <span className="file-btn-text">New Folder</span>
            </button>

            <button
              className="btn btn-xs btn-secondary"
              onClick={onNewFile}
              title="New File"
            >
              <FilePlus size={14} color="var(--accent)" />
              <span className="file-btn-text">New File</span>
            </button>

            <button
              className="btn btn-xs btn-primary file-upload-btn"
              onClick={onUploadClick}
              disabled={uploading}
              title="Upload Files"
            >
              <Upload size={14} className={uploading ? 'animate-bounce' : ''} />
              <span>{uploading ? 'Uploading…' : 'Upload'}</span>
            </button>
          </div>
        )}

        {selectedCount > 0 && (
          <button
            className="btn btn-xs btn-ghost file-delete-selected-btn"
            onClick={onDeleteSelected}
            style={{ color: '#f87171' }}
            title="Delete selected items"
          >
            <Trash2 size={14} />
            <span>Delete ({selectedCount})</span>
          </button>
        )}
      </div>
    </div>
  );
};
