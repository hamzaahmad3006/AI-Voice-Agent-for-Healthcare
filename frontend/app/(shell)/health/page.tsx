'use client';

import { useHealth } from '@/hooks/useHealth';
import type { ServiceStatus } from '@/types/health';

function ServiceCard({ label, icon, status }: { label: string; icon: string; status: ServiceStatus }): JSX.Element {
  const isOk = status === 'ok';
  return (
    <div className="flex items-center justify-between rounded-xl border border-outline-variant bg-surface-container-lowest p-md shadow-sm">
      <div className="flex items-center gap-sm">
        <span className={`material-symbols-outlined text-[24px] ${isOk ? 'text-secondary' : 'text-error'}`}>{icon}</span>
        <div>
          <p className="font-body-md text-body-md text-on-surface">{label}</p>
          <p className="font-caption text-caption text-on-surface-variant">Last checked just now</p>
        </div>
      </div>
      <span
        className={`rounded-full px-sm py-xs font-label-caps text-label-caps ${
          isOk
            ? 'bg-secondary-container text-on-secondary-container'
            : status === 'degraded'
            ? 'bg-primary-fixed text-on-primary-fixed-variant'
            : 'bg-error-container text-on-error-container'
        }`}
      >
        {status.toUpperCase()}
      </span>
    </div>
  );
}

export default function HealthPage(): JSX.Element {
  const { health, loading, error } = useHealth();

  return (
    <div>
      <div className="mb-md">
        <h2 className="font-headline-md text-headline-md text-on-surface">Service Health</h2>
        <p className="font-body-md text-body-md text-on-surface-variant mt-xs">
          Checks run every 15 seconds automatically.
        </p>
      </div>

      {error !== null && (
        <div className="mb-md rounded-lg bg-error-container px-md py-sm">
          <p className="font-caption text-caption text-on-error-container">{error}</p>
        </div>
      )}

      {loading && (
        <div className="flex justify-center py-xl">
          <p className="font-body-md text-body-md text-on-surface-variant">Checking services…</p>
        </div>
      )}

      {health !== null && (
        <>
          {/* Overall status banner */}
          <div
            className={`mb-md flex items-center gap-sm rounded-xl border p-md ${
              health.status === 'ok'
                ? 'border-secondary-container bg-secondary-container/30'
                : 'bg-primary-fixed/20 border-primary-fixed'
            }`}
          >
            <span className={`material-symbols-outlined text-[28px] ${health.status === 'ok' ? 'text-secondary' : 'text-primary'}`}>
              {health.status === 'ok' ? 'check_circle' : 'warning'}
            </span>
            <div>
              <p className="font-headline-md text-headline-md text-on-surface">
                {health.status === 'ok' ? 'All Systems Operational' : 'System Degraded'}
              </p>
              <p className="font-caption text-caption text-on-surface-variant">
                Environment: {health.environment}
              </p>
            </div>
          </div>

          {/* Service list */}
          <div className="flex flex-col gap-md">
            <ServiceCard label="Backend API"          icon="cloud"          status={health.status} />
            <ServiceCard label="Redis (session store)" icon="storage"        status={health.redis} />
          </div>
        </>
      )}
    </div>
  );
}
