export interface StorageDiskItem {
  filesystem?: string;
  size: string;
  used: string;
  available?: string;
  use_percent?: string;
  mount_point?: string;
  fs?: string;
  avail?: string;
  use_pct?: string;
  mount?: string;
  is_external?: boolean;
  pct_num?: number;
}

export interface StorageOverviewResponse {
  disks: StorageDiskItem[];
}

export type FileCategory =
  | 'folder'
  | 'code'
  | 'image'
  | 'video'
  | 'audio'
  | 'archive'
  | 'document'
  | 'text'
  | 'binary';

export interface FileItem {
  name: string;
  path: string;
  is_dir: boolean;
  is_symlink: boolean;
  symlink_target?: string | null;
  size: number;
  size_human: string;
  modified: number;
  modified_human: string;
  permissions: string;
  owner: string;
  group: string;
  extension: string;
  mime_type: string;
  category: FileCategory;
  is_writable: boolean;
}

export interface DiskUsageSummary {
  total: number;
  total_human: string;
  used: number;
  used_human: string;
  free: number;
  free_human: string;
  use_pct: number;
}

export interface FileListResponse {
  current_path: string;
  parent_path: string | null;
  home_path: string;
  is_writable: boolean;
  total_items: number;
  total_dirs: number;
  total_files: number;
  disk: DiskUsageSummary;
  items: FileItem[];
}

export interface FilePreviewResponse {
  name: string;
  path: string;
  size: number;
  size_human: string;
  mime_type: string;
  category: string;
  is_text: boolean;
  content: string | null;
  truncated: boolean;
  line_count: number;
  modified: string;
  permissions: string;
  is_writable: boolean;
}

export interface BookmarkItem {
  name: string;
  path: string;
  icon: string;
  type: 'user' | 'system';
}

export interface BookmarksResponse {
  bookmarks: BookmarkItem[];
  disks: StorageDiskItem[];
}

