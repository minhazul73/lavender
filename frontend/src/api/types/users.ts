import { UserProfile } from './auth';

export interface UserSessionItem {
  user: string;
  tty: string;
  from?: string;
  host?: string;
  login_time?: string;
  idle?: string;
}

export interface UserStorageInfo {
  total_gb: number;
  used_gb: number;
  free_gb: number;
  percent_used: number;
}

export interface UserItem {
  name?: string;
  username?: string;
  uid: number;
  gid: number;
  home: string;
  shell: string;
  comment?: string;
  groups: string[];
  is_human?: boolean;
  is_admin?: boolean;
  is_current?: boolean;
  is_active?: boolean;
  home_exists?: boolean;
  home_storage?: UserStorageInfo | null;
  ssh_keys_count?: number;
}

export interface SshKeyItem {
  index: number;
  type: string;
  preview: string;
  comment: string;
  raw?: string;
}

export interface GroupCategoryItem {
  name: string;
  gid: number;
  members: string[];
  category: 'Privileged' | 'Hardware' | 'Services' | 'System' | 'General' | string;
  description: string;
  member_count: number;
}

export interface LoginHistoryItem {
  user: string;
  tty: string;
  host: string;
  time: string;
}

export interface SecurityPosture {
  elevation_engine?: string;
  has_sudo?: boolean;
  has_doas?: boolean;
  visudo_ok?: boolean;
  visudo_msg?: string;
  sshd_active?: boolean;
  root_ssh_login?: string;
  password_auth?: string;
}

export interface UsersMetrics {
  active_sessions_count: number;
  human_users_count: number;
  total_ssh_keys: number;
  is_elevated: boolean;
}

export interface UsersOverviewResponse {
  human_users: UserItem[];
  system_users: UserItem[];
  groups_categorized: GroupCategoryItem[] | Record<string, string[]>;
  active_sessions: UserSessionItem[];
  login_history: LoginHistoryItem[];
  security: SecurityPosture;
  metrics: UsersMetrics;
  current_user?: UserProfile;
  sudoers?: Record<string, unknown>;
}

