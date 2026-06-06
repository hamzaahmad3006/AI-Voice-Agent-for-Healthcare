import type { HealthStatus } from '@/types/health';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API}/health`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`GET /health failed: ${res.status}`);
  const raw = (await res.json()) as Record<string, unknown>;
  return {
    status: raw['status'] as HealthStatus['status'],
    environment: raw['environment'] as string,
    redis: (raw['redis'] as HealthStatus['redis']) ?? 'ok',
  };
}
