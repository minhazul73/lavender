export interface ServiceItem {
  unit: string;
  name?: string;
  load?: string;
  load_state?: string;
  active?: string;
  active_state?: string;
  sub?: string;
  sub_state?: string;
  description?: string;
  scope?: string;
}

export interface ServicesListResponse {
  services: ServiceItem[];
  count: number;
}
