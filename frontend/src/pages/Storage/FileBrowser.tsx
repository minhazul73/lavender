import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../../api/client';
import {
  FileItem,
  FileListResponse,
  BookmarkItem,
  BookmarksResponse,
  StorageDiskItem,
} from '../../api/types';
import { useToast } from '../../context/ToastContext';
import { useOptionalAuth } from '../../context/AuthContext';
import { ConfirmModal } from '../../components/common/ConfirmModal';
import { FilePreviewModal } from './FilePreviewModal';
import { CreateFolderModal, CreateFileModal, RenameModal } from './FileModals';
import {
  Folder,
  HardDrive,
  Disc,
  Unplug,
  Upload,
  Lock,
  Unlock,
  X,
} from 'lucide-react';
import { FileBreadcrumbs, getBookmarkIcon } from './FileBreadcrumbs';
import { FileToolbar } from './FileToolbar';
import { FileListTable } from './FileListTable';

interface FileBrowserProps {
  disks: StorageDiskItem[];
  onUnmountClick: (disk: StorageDiskItem) => void;
  onRefreshStorage: () => void;
}

export const FileBrowser: React.FC<FileBrowserProps> = ({
  disks,
  onUnmountClick,
  onRefreshStorage,
}) => {
  const { addToast } = useToast();
  const auth = useOptionalAuth();
  const session = auth?.session;
  const isElevated = Boolean(auth?.isElevated);

  // Navigation and data state
  const [currentPath, setCurrentPath] = useState<string>('');
  const currentPathRef = useRef<string>('');
  currentPathRef.current = currentPath;
  const [history, setHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState<number>(-1);
  const historyRef = useRef<string[]>([]);
  historyRef.current = history;
  const historyIdxRef = useRef<number>(-1);
  historyIdxRef.current = historyIdx;

  const [fileData, setFileData] = useState<FileListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canWrite = Boolean(fileData?.is_writable || session?.is_admin || isElevated || session?.can_elevate);

  // Bookmarks & options
  const [bookmarks, setBookmarks] = useState<BookmarkItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [showHidden, setShowHidden] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const [sortBy, setSortBy] = useState<'name' | 'size' | 'modified'>('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [isEditingPath, setIsEditingPath] = useState(false);
  const [manualPath, setManualPath] = useState('');
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  const [mobileLocationsOpen, setMobileLocationsOpen] = useState(false);

  // Close mobile drawer on Escape key
  useEffect(() => {
    if (!mobileLocationsOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMobileLocationsOpen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [mobileLocationsOpen]);

  // Modals state
  const [previewFilePath, setPreviewFilePath] = useState<string | null>(null);
  const [createFolderOpen, setCreateFolderOpen] = useState(false);
  const [createFileOpen, setCreateFileOpen] = useState(false);
  const [renameItem, setRenameItem] = useState<FileItem | null>(null);
  const [deleteTargets, setDeleteTargets] = useState<string[] | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // Drag and drop & upload
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Load Bookmarks once
  useEffect(() => {
    api
      .get<BookmarksResponse>('/api/storage/bookmarks')
      .then((res) => {
        if (res && Array.isArray(res.bookmarks)) setBookmarks(res.bookmarks);
      })
      .catch(() => {});
  }, []);

  // Fetch Directory
  const loadDirectory = useCallback(
    async (targetPath?: string, isRefresh = false, addToHistory = true) => {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      setError(null);

      // Determine path: use supplied targetPath, or fall back to currentPathRef.current, or empty string (for home)
      const pathToFetch = targetPath !== undefined ? targetPath : currentPathRef.current;
      const pathQuery = pathToFetch ? `path=${encodeURIComponent(pathToFetch)}&` : '';
      const hiddenQuery = `show_hidden=${showHidden}&`;
      const sortQuery = `sort_by=${sortBy}&order=${sortOrder}`;

      try {
        const res = await api.get<FileListResponse>(
          `/api/storage/files?${pathQuery}${hiddenQuery}${sortQuery}`
        );
        const resolvedPath = res?.current_path || '/';
        const itemsList = Array.isArray(res?.items) ? res.items : [];
        const safeData: FileListResponse = {
          current_path: resolvedPath,
          parent_path: res?.parent_path || null,
          home_path: res?.home_path || resolvedPath,
          is_writable: res?.is_writable ?? true,
          total_items: res?.total_items ?? itemsList.length,
          total_dirs: res?.total_dirs ?? 0,
          total_files: res?.total_files ?? 0,
          disk: res?.disk || {
            total: 0, total_human: '—', used: 0, used_human: '—', free: 0, free_human: '—', use_pct: 0,
          },
          items: itemsList,
        };

        setFileData(safeData);
        setCurrentPath(resolvedPath);
        currentPathRef.current = resolvedPath;
        setManualPath(resolvedPath);
        setSelectedPaths(new Set());

        if (addToHistory && resolvedPath) {
          const currentHist = historyRef.current;
          const currentIdx = historyIdxRef.current;
          const upToCurrent = currentIdx >= 0 ? currentHist.slice(0, currentIdx + 1) : [];
          if (upToCurrent[upToCurrent.length - 1] !== resolvedPath) {
            const next = [...upToCurrent, resolvedPath];
            setHistory(next);
            historyRef.current = next;
            const newIdx = next.length - 1;
            setHistoryIdx(newIdx);
            historyIdxRef.current = newIdx;
          }
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to list directory';
        setError(msg);
        addToast(msg, 'error');
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [showHidden, sortBy, sortOrder, addToast]
  );

  // Initial load once on mount
  useEffect(() => {
    loadDirectory('', false, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Re-fetch current directory when sorting or showHidden changes
  useEffect(() => {
    if (currentPathRef.current) {
      loadDirectory(currentPathRef.current, true, false);
    }
  }, [showHidden, sortBy, sortOrder, loadDirectory]);

  // Navigation handlers
  const navigateTo = (path: string) => {
    setIsEditingPath(false);
    setSearchQuery('');
    loadDirectory(path, false, true);
  };

  const handleGoBack = () => {
    if (historyIdxRef.current > 0) {
      const nextIdx = historyIdxRef.current - 1;
      setHistoryIdx(nextIdx);
      historyIdxRef.current = nextIdx;
      loadDirectory(historyRef.current[nextIdx], true, false);
    }
  };

  const handleGoForward = () => {
    if (historyIdxRef.current < historyRef.current.length - 1) {
      const nextIdx = historyIdxRef.current + 1;
      setHistoryIdx(nextIdx);
      historyIdxRef.current = nextIdx;
      loadDirectory(historyRef.current[nextIdx], true, false);
    }
  };

  const handleGoUp = () => {
    if (fileData?.parent_path) navigateTo(fileData.parent_path);
  };

  const handleManualPathSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (manualPath.trim()) navigateTo(manualPath.trim());
  };

  const handleCopyCurrentPath = async () => {
    if (!currentPath) return;
    try {
      await navigator.clipboard.writeText(currentPath);
      addToast('Path copied to clipboard', 'info');
    } catch {
      addToast('Failed to copy path', 'error');
    }
  };

  // Selection handlers
  const toggleSelect = (path: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setSelectedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (!fileData) return;
    const filtered = filteredItems;
    if (selectedPaths.size === filtered.length) {
      setSelectedPaths(new Set());
    } else {
      setSelectedPaths(new Set(filtered.map((item) => item.path)));
    }
  };

  // Upload handlers
  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0 || !currentPath) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('path', currentPath);
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    try {
      const res = await api.postForm<{ success: boolean; count: number }>('/api/storage/upload', formData);
      if (res.success) {
        addToast(`Successfully uploaded ${res.count} file(s)`, 'success');
        await loadDirectory(currentPath, true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'File upload failed';
      addToast(msg, 'error');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };
  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    if (e.dataTransfer.files?.length) {
      await handleFileUpload(e.dataTransfer.files);
    }
  };

  // CRUD Actions
  const handleCreateFolder = async (name: string) => {
    setActionLoading(true);
    try {
      await api.post('/api/storage/mkdir', { path: currentPath, name });
      addToast(`Folder '${name}' created`, 'success');
      setCreateFolderOpen(false);
      await loadDirectory(currentPath, true);
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : 'Failed to create folder', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateFile = async (name: string, content: string) => {
    setActionLoading(true);
    try {
      await api.post('/api/storage/file/create', { path: currentPath, name, content });
      addToast(`File '${name}' created`, 'success');
      setCreateFileOpen(false);
      await loadDirectory(currentPath, true);
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : 'Failed to create file', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRename = async (newName: string) => {
    if (!renameItem) return;
    setActionLoading(true);
    try {
      await api.post('/api/storage/rename', { old_path: renameItem.path, new_name: newName });
      addToast(`Renamed to '${newName}'`, 'success');
      setRenameItem(null);
      await loadDirectory(currentPath, true);
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : 'Failed to rename', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTargets || deleteTargets.length === 0) return;
    setDeleteLoading(true);
    try {
      const res = await api.post<{ success: boolean; deleted: string[] }>('/api/storage/delete', {
        paths: deleteTargets,
      });
      if (res.success) {
        addToast(`Deleted ${res.deleted.length} item(s)`, 'success');
        setDeleteTargets(null);
        setSelectedPaths(new Set());
        await loadDirectory(currentPath, true);
      }
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : 'Failed to delete', 'error');
    } finally {
      setDeleteLoading(false);
    }
  };

  // Filtered and sorted items
  const items = fileData?.items || [];
  const filteredItems = items.filter((item) =>
    item.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Compute selected size
  const selectedItemsList = items.filter((i) => selectedPaths.has(i.path));
  const selectedSizeSum = selectedItemsList.reduce((acc, curr) => acc + (curr.size || 0), 0);

  // Break current path into breadcrumb tokens
  const breadcrumbParts: { name: string; fullPath: string }[] = [];
  if (currentPath) {
    const parts = currentPath.split('/').filter(Boolean);
    breadcrumbParts.push({ name: 'Root', fullPath: '/' });
    let acc = '';
    for (const part of parts) {
      acc += '/' + part;
      breadcrumbParts.push({ name: part, fullPath: acc });
    }
  }

  return (
    <div
      className="file-workspace"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drag & Drop Visual Indicator */}
      {isDragOver && (
        <div className="file-drop-overlay">
          <Upload size={48} className="animate-bounce" />
          <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 600 }}>Drop files to upload here</h3>
          <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Destination: {currentPath}
          </p>
        </div>
      )}

      {/* Hidden File Input for Toolbar Upload */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        style={{ display: 'none' }}
        onChange={(e) => handleFileUpload(e.target.files)}
      />

      {/* Mobile Drawer Backdrop */}
      <div
        className={`file-sidebar-backdrop ${mobileLocationsOpen ? 'open' : ''}`}
        onClick={() => setMobileLocationsOpen(false)}
        aria-hidden="true"
      />

      {/* ── Left Sidebar: Drives & Places ───────────────────────── */}
      <aside className={`file-sidebar ${mobileLocationsOpen ? 'open' : ''}`}>
        {/* Mobile Drawer Header */}
        <div className="file-sidebar-mobile-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <HardDrive size={18} color="var(--purple)" />
            <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>Locations & Drives</span>
          </div>
          <button
            className="btn btn-xs btn-ghost"
            onClick={() => setMobileLocationsOpen(false)}
            title="Close locations drawer"
            aria-label="Close locations drawer"
            style={{ padding: '4px' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Pinned Places / Bookmarks */}
        <div>
          <div className="file-sidebar-section-title">
            <span>Places</span>
            <Folder size={13} />
          </div>
          <div className="file-sidebar-list">
            {bookmarks.map((bm) => (
              <button
                key={bm.path}
                className={`file-sidebar-item ${currentPath === bm.path ? 'active' : ''}`}
                onClick={() => {
                  navigateTo(bm.path);
                  setMobileLocationsOpen(false);
                }}
                title={bm.path}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flex: 1 }}>
                  {getBookmarkIcon(bm.icon)}
                  <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{bm.name}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Drives & Partitions */}
        <div>
          <div className="file-sidebar-section-title">
            <span>Drives & Partitions</span>
            <HardDrive size={13} />
          </div>
          <div className="file-sidebar-list">
            {disks.map((d, idx) => {
              const mount = d.mount_point || d.mount || '/';
              const fs = d.filesystem || d.fs || 'unknown';
              const isActive = Boolean(currentPath && mount && (currentPath === mount || currentPath.startsWith(mount + '/')));
              const isSystemMount = mount === '/' || mount.startsWith('/sys') || mount.startsWith('/proc') || mount.startsWith('/dev') || mount.startsWith('/boot') || mount.startsWith('/run');
              const pct = typeof d.pct_num === 'number' ? d.pct_num : parseInt(String(d.use_percent || d.use_pct || '0').replace('%', ''), 10) || 0;
              const usePercent = d.use_percent || d.use_pct || (typeof d.pct_num === 'number' ? `${d.pct_num}%` : `${pct}%`);

              return (
                <div
                  key={mount || idx}
                  className={`file-drive-card ${isActive ? 'active' : ''}`}
                  onClick={() => {
                    navigateTo(mount);
                    setMobileLocationsOpen(false);
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0, flex: 1 }}>
                      <Disc size={15} style={{ flexShrink: 0, color: 'var(--purple)' }} />
                      <strong style={{ fontSize: '0.82rem', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: 0 }} title={mount}>
                        {mount}
                      </strong>
                    </div>

                    {!isSystemMount && (
                      <button
                        className="btn btn-xs btn-ghost"
                        title="Unmount Partition"
                        onClick={(e) => {
                          e.stopPropagation();
                          onUnmountClick({ ...d, mount_point: mount, filesystem: fs });
                        }}
                        style={{ color: '#f87171', padding: '2px 6px', flexShrink: 0, display: 'inline-flex', alignItems: 'center', gap: '3px' }}
                      >
                        <Unplug size={11} />
                        <span style={{ fontSize: '0.72rem' }}>Unmount</span>
                      </button>
                    )}
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '5px' }}>
                    <span className="font-mono" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: 0, flex: 1 }} title={fs}>
                      {fs}
                    </span>
                    <span className="badge badge-lavender" style={{ fontSize: '0.68rem', padding: '1px 5px', flexShrink: 0 }}>
                      {usePercent}
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    <span>Used: {d.used || '—'}</span>
                    <span className="font-mono">{d.size || '—'}</span>
                  </div>

                  <div className="progress-bar-outer" style={{ height: '4px', marginTop: '6px' }}>
                    <div
                      className={`progress-bar-inner ${pct > 85 ? 'crit' : pct > 70 ? 'warn' : ''}`}
                      style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </aside>

      {/* ── Main Explorer Pane ─────────────────────────────────── */}
      <section className="file-explorer-main">
        <FileBreadcrumbs
          currentPath={currentPath}
          onNavigate={navigateTo}
          onGoBack={handleGoBack}
          canGoBack={historyIdx > 0}
          onGoForward={handleGoForward}
          canGoForward={historyIdx < history.length - 1}
          onGoUp={handleGoUp}
          canGoUp={Boolean(fileData?.parent_path)}
          onRefresh={() => {
            loadDirectory(currentPath, true);
            onRefreshStorage();
          }}
          refreshing={refreshing}
          onOpenMobileLocations={() => setMobileLocationsOpen(true)}
          onCopyPath={handleCopyCurrentPath}
          isEditingPath={isEditingPath}
          setIsEditingPath={setIsEditingPath}
          manualPath={manualPath}
          setManualPath={setManualPath}
          onSubmitManualPath={handleManualPathSubmit}
          breadcrumbParts={breadcrumbParts}
          bookmarks={bookmarks}
          disks={disks}
        />

        <FileToolbar
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          showHidden={showHidden}
          setShowHidden={setShowHidden}
          viewMode={viewMode}
          setViewMode={setViewMode}
          canWrite={canWrite}
          onNewFolder={() => setCreateFolderOpen(true)}
          onNewFile={() => setCreateFileOpen(true)}
          onUploadClick={() => fileInputRef.current?.click()}
          uploading={uploading}
          selectedCount={selectedPaths.size}
          onDeleteSelected={() => setDeleteTargets(Array.from(selectedPaths))}
        />

        <FileListTable
          loading={loading}
          error={error}
          items={filteredItems}
          searchQuery={searchQuery}
          viewMode={viewMode}
          selectedPaths={selectedPaths}
          onToggleSelectAll={toggleSelectAll}
          onToggleSelect={toggleSelect}
          onNavigate={navigateTo}
          onPreview={(path) => setPreviewFilePath(path)}
          onRename={(item) => setRenameItem(item)}
          onDelete={(paths) => setDeleteTargets(paths)}
          sortBy={sortBy}
          sortOrder={sortOrder}
          onSort={(column) => {
            if (sortBy === column) setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
            else {
              setSortBy(column);
              setSortOrder(column === 'name' ? 'asc' : 'desc');
            }
          }}
          onRetry={() => loadDirectory(currentPath, true)}
        />

        {/* ── Status Bar ─────────────────────────────────────────── */}
        <div className="file-status-bar">
          <div className="file-status-bar-group">
            <span>
              {fileData?.total_items || 0} items ({fileData?.total_dirs || 0} folders, {fileData?.total_files || 0} files)
            </span>
            {selectedPaths.size > 0 && (
              <span style={{ color: 'var(--lavender-300)' }}>
                {selectedPaths.size} selected ({selectedSizeSum > 0 ? (selectedSizeSum / (1024 * 1024)).toFixed(1) + ' MB' : '0 B'})
              </span>
            )}
          </div>

          <div className="file-status-bar-group">
            {fileData?.disk && (
              <span>
                Free space: <strong style={{ color: 'var(--text-primary)' }}>{fileData.disk.free_human}</strong> of {fileData.disk.total_human} ({fileData.disk.use_pct}% used)
              </span>
            )}

            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              {fileData?.is_writable ? (
                <>
                  <Unlock size={12} color="var(--green)" />
                  <span style={{ color: 'var(--green)' }}>Writable</span>
                </>
              ) : (session?.is_admin || isElevated) ? (
                <>
                  <Unlock size={12} color="var(--purple)" />
                  <span className="badge badge-lavender" style={{ fontSize: '0.68rem', padding: '1px 5px' }}>
                    Root (Admin Write)
                  </span>
                </>
              ) : (
                <>
                  <Lock size={12} color="#fbbf24" />
                  <span style={{ color: '#fbbf24' }}>Read-Only</span>
                </>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── Modals ─────────────────────────────────────────────── */}
      <FilePreviewModal
        isOpen={Boolean(previewFilePath)}
        filePath={previewFilePath}
        onClose={() => setPreviewFilePath(null)}
        onSaveSuccess={() => loadDirectory(currentPath, true)}
      />
      <CreateFolderModal
        isOpen={createFolderOpen}
        parentPath={currentPath}
        onClose={() => setCreateFolderOpen(false)}
        onSubmit={handleCreateFolder}
        loading={actionLoading}
      />
      <CreateFileModal
        isOpen={createFileOpen}
        parentPath={currentPath}
        onClose={() => setCreateFileOpen(false)}
        onSubmit={handleCreateFile}
        loading={actionLoading}
      />
      {renameItem && (
        <RenameModal
          isOpen={Boolean(renameItem)}
          currentPath={renameItem.path}
          currentName={renameItem.name}
          onClose={() => setRenameItem(null)}
          onSubmit={handleRename}
          loading={actionLoading}
        />
      )}
      {deleteTargets && (
        <ConfirmModal
          isOpen={Boolean(deleteTargets)}
          onClose={() => setDeleteTargets(null)}
          onConfirm={handleDeleteConfirm}
          isLoading={deleteLoading}
          isDanger={true}
          title="Delete Item(s)"
          message={`Are you sure you want to permanently delete ${deleteTargets.length} item(s)? This action cannot be undone.`}
          confirmLabel="Delete Permanently"
        />
      )}
    </div>
  );
};
