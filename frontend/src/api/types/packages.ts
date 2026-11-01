export interface PackageItem {
  name: string;
  version?: string;
  description?: string;
  installed?: boolean;
  upgradable?: boolean;
  new_version?: string;
}

export interface PackagesOverviewResponse {
  backend: string;
  backend_name: string;
  backend_short: string;
  installed_count: number;
  upgradable_count: number;
  upgradable: PackageItem[];
  installed: PackageItem[];
}

