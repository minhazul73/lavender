import React from 'react';
import {
  FolderTree, ChevronLeft, ChevronRight, CornerLeftUp, RefreshCw,
  Copy, HardDrive, Disc, Home, Monitor, FileText, Download,
  Image, Video, Music, Settings, Terminal, Zap, Folder
} from 'lucide-react';
import type { BookmarkItem, StorageDiskItem } from '../../api/types';

export const getBookmarkIcon = (icon: string) => {
  switch (icon) {
    case 'home': return <Home size={15} />;
    case 'monitor': return <Monitor size={15} />;
    case 'file-text': return <FileText size={15} />;
    case 'download': return <Download size={15} />;
    case 'image': return <Image size={15} />;
    case 'video': return <Video size={15} />;
    case 'music': return <Music size={15} />;
    case 'hard-drive': return <HardDrive size={15} />;
    case 'settings': return <Settings size={15} />;
    case 'terminal': return <Terminal size={15} />;
    case 'zap': return <Zap size={15} />;
    default: return <Folder size={15} />;
  }
};

export interface FileBreadcrumbsProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  onGoBack: () => void;
  canGoBack: boolean;
  onGoForward: () => void;
  canGoForward: boolean;
  onGoUp: () => void;
  canGoUp: boolean;
  onRefresh: () => void;
  refreshing: boolean;
  onOpenMobileLocations: () => void;
  onCopyPath: () => void;
  isEditingPath: boolean;
  setIsEditingPath: (editing: boolean) => void;
  manualPath: string;
  setManualPath: (path: string) => void;
  onSubmitManualPath: (e: React.FormEvent) => void;
  breadcrumbParts: Array<{ name: string; fullPath: string }>;
  bookmarks: BookmarkItem[];
  disks: StorageDiskItem[];
}

export const FileBreadcrumbs: React.FC<FileBreadcrumbsProps> = ({
  currentPath,
  onNavigate,
  onGoBack,
  canGoBack,
  onGoForward,
  canGoForward,
  onGoUp,
  canGoUp,
  onRefresh,
  refreshing,
  onOpenMobileLocations,
  onCopyPath,
  isEditingPath,
  setIsEditingPath,
  manualPath,
  setManualPath,
  onSubmitManualPath,
  breadcrumbParts,
  bookmarks,
  disks,
}) => {
  return (
    <>
      {/* Navigation & Breadcrumbs Bar */}
      <div className="file-breadcrumbs-bar">
        <div className="file-nav-row">
          <div className="file-nav-buttons">
            <button
              className="file-nav-btn file-locations-toggle-btn"
              onClick={onOpenMobileLocations}
              title="Locations & Drives"
              aria-label="Open locations drawer"
            >
              <FolderTree size={15} />
              <span className="file-locations-label">Places</span>
            </button>

            <button className="file-nav-btn" onClick={onGoBack} disabled={!canGoBack} title="Back">
              <ChevronLeft size={16} />
            </button>
            <button className="file-nav-btn" onClick={onGoForward} disabled={!canGoForward} title="Forward">
              <ChevronRight size={16} />
            </button>
            <button className="file-nav-btn" onClick={onGoUp} disabled={!canGoUp} title="Up one level">
              <CornerLeftUp size={16} />
            </button>
            <button className="file-nav-btn" onClick={onRefresh} disabled={refreshing} title="Refresh">
              <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            </button>
          </div>

          <button className="file-nav-btn file-copy-path-btn-mobile" onClick={onCopyPath} title="Copy current path">
            <Copy size={14} />
          </button>
        </div>

        {/* Breadcrumb / Path Input Switcher */}
        {isEditingPath ? (
          <form onSubmit={onSubmitManualPath} style={{ flex: 1, display: 'flex', gap: '6px' }}>
            <input
              type="text"
              className="file-path-input"
              value={manualPath}
              onChange={(e) => setManualPath(e.target.value)}
              autoFocus
              onBlur={() => {
                if (manualPath === currentPath) setIsEditingPath(false);
              }}
            />
            <button type="submit" className="btn btn-xs btn-primary">Go</button>
            <button
              type="button"
              className="btn btn-xs btn-ghost"
              onClick={() => {
                setManualPath(currentPath);
                setIsEditingPath(false);
              }}
            >
              Cancel
            </button>
          </form>
        ) : (
          <div
            className="file-breadcrumbs-trail"
            onClick={() => setIsEditingPath(true)}
            title="Click to manually edit path"
          >
            {breadcrumbParts.map((b, idx) => {
              const isLast = idx === breadcrumbParts.length - 1;
              return (
                <React.Fragment key={b.fullPath}>
                  <button
                    type="button"
                    className={`file-breadcrumb-segment ${isLast ? 'current' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onNavigate(b.fullPath);
                    }}
                  >
                    {idx === 0 && <HardDrive size={13} style={{ marginRight: '2px' }} />}
                    <span>{b.name}</span>
                  </button>
                  {!isLast && <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>/</span>}
                </React.Fragment>
              );
            })}
          </div>
        )}

        <button className="file-nav-btn file-copy-path-btn-desktop" onClick={onCopyPath} title="Copy current path">
          <Copy size={14} />
        </button>
      </div>

      {/* Quick Locations Horizontal Chip Bar on Mobile */}
      <div className="file-quick-places-bar">
        {bookmarks.slice(0, 6).map((bm) => {
          const isActive = currentPath === bm.path;
          return (
            <button
              key={bm.path}
              className={`file-quick-place-chip ${isActive ? 'active' : ''}`}
              onClick={() => onNavigate(bm.path)}
              title={bm.path}
            >
              {getBookmarkIcon(bm.icon)}
              <span>{bm.name}</span>
            </button>
          );
        })}
        {disks.map((d, i) => {
          const mount = d.mount_point || d.mount || '/';
          const isActive = Boolean(
            currentPath && mount && (currentPath === mount || currentPath.startsWith(mount + '/'))
          );
          return (
            <button
              key={mount || i}
              className={`file-quick-place-chip ${isActive ? 'active' : ''}`}
              onClick={() => onNavigate(mount)}
              title={mount}
            >
              <Disc size={12} color="var(--purple)" />
              <span>{mount}</span>
            </button>
          );
        })}
      </div>
    </>
  );
};
