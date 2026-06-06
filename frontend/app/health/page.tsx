'use client';

import { useHealth } from '@/hooks/useHealth';

const STATUS_STYLE: Record<string, string> = {
  ok:       'bg-emerald-100 text-emerald-700',
  degraded: 'bg-amber-100 text-amber-700',
  error:    'bg-red-100 text-red-700',
};

const STATUS_DOT: Record<string, string> = {
  ok:       'bg-emerald-500',
  degraded: 'bg-amber-500',
  error:    'bg-red-500',
};

function ServiceRow({ label, status }: { label: string; status: string }): JSX.Element {
  const style = STATUS_STYLE[status] ?? STATUS_STYLE['error'];
  const dot   = STATUS_DOT[status]   ?? STATUS_DOT['error'];
  return (
    <div className="flex items-center justify-between rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <span className={`h-2.5 w-2.5 rounded-full ${dot}`} />
        <span className="text-sm font-semibold text-gray-900">{label}</span>
      </div>
      <span className={`rounded-full px-3 py-1 text-xs font-medium ${style}`}>
        {status}
      </span>
    </div>
  );
}

export default function HealthPage(): JSX.Element {
  const { health, loading, error } = useHealth();

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900">Service Health</h2>
        <p className="mt-1 text-sm text-gray-500">Checks run every 15 seconds.</p>
      </div>

      {error !== null && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && (
        <div className="flex justify-center py-16">
          <span className="text-sm text-gray-400">Checking services…</span>
        </div>
      )}

      {health !== null && (
        <>
          {/* Overall banner */}
          <div
            className={`mb-6 flex items-center gap-3 rounded-xl border p-5 ${health.status === 'ok' ? 'border-emerald-200 bg-emerald-50' : 'border-amber-200 bg-amber-50'}`}
          >
            <span className={`h-3 w-3 rounded-full ${health.status === 'ok' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
            <div>
              <p className="text-sm font-semibold text-gray-900">
                System {health.status === 'ok' ? 'Operational' : 'Degraded'}
              </p>
              <p className="text-xs text-gray-500">Environment: {health.environment}</p>
            </div>
          </div>

          {/* Service rows */}
          <div className="grid gap-3">
            <ServiceRow label="Backend API" status={health.status} />
            <ServiceRow label="Redis (session store)" status={health.redis} />
          </div>
        </>
      )}
    </div>
  );
}
