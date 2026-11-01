export interface UserProfile {
  username: string;
  uid: number;
  gid: number;
  home: string;
  shell: string;
  groups: string[];
  is_admin: boolean;
  can_elevate: boolean;
  admin_remaining_seconds: number;
  connected?: boolean;
}

export interface LoginResponse {
  success: boolean;
  username: string;
  redirect: string;
  is_admin: boolean;
  can_elevate: boolean;
}

export interface ElevationResponse {
  success: boolean;
  is_admin: boolean;
  expires_in: number;
}
