// Health and observability types for the Health page

export type ServiceStatus = 'ok' | 'degraded' | 'error';

export interface HealthStatus {
  status: ServiceStatus;
  environment: string;
}

export interface ServiceHealth {
  name: string;
  status: ServiceStatus;
  latencyMs: number | null;
  lastChecked: string; // ISO 8601
}

export interface HealthState {
  health: HealthStatus | null;
  loading: boolean;
  error: string | null;
}
