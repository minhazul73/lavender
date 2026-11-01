export interface PowerStateResponse {
  active_governor: string;
  available_governors: string[];
  scheduled?: {
    action: string;
    time: string;
    remaining_minutes: number;
  } | null;
}

