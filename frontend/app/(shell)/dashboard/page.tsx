'use client';

import Link from 'next/link';

import StateBadge from '@/components/StateBadge';
import { useLiveCall } from '@/hooks/useLiveCall';

function MetricCard({
  icon,
  label,
  value,
  accent = false,
}: {
  icon: string;
  label: string;
  value: number | string;
  accent?: boolean;
}): JSX.Element {
  return (
    <div className="rounded-xl border border-outline-variant bg-surface-container-lowest p-md shadow-sm">
      <div className="flex items-center gap-sm mb-xs">
        <span className={`material-symbols-outlined text-[20px] ${accent ? 'text-primary' : 'text-secondary'}`}>
          {icon}
        </span>
        <p className="font-label-caps text-label-caps text-on-surface-variant">{label}</p>
      </div>
      <p className={`font-headline-md text-headline-md ${accent ? 'text-primary' : 'text-on-surface'}`}>
        {value}
      </p>
    </div>
  );
}

export default function DashboardPage(): JSX.Element {
  const { activeCalls, totalToday, bookedToday, loading, error } = useLiveCall();

  return (
    <div>
      {/* Page header */}
      <div className="mb-md">
        <h2 className="font-headline-md text-headline-md text-on-surface">Overview</h2>
        <p className="font-body-md text-body-md text-on-surface-variant mt-xs">
          Real-time call activity and booking metrics.
        </p>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-md lg:grid-cols-4 mb-md">
        <MetricCard icon="phone_in_talk"   label="ACTIVE CALLS"   value={loading ? '—' : activeCalls.length} accent />
        <MetricCard icon="list_alt"        label="TOTAL SESSIONS" value={loading ? '—' : totalToday} />
        <MetricCard icon="event_available" label="BOOKINGS"       value={loading ? '—' : bookedToday} />
        <MetricCard icon="support_agent"   label="HANDOFFS"       value={loading ? '—' : activeCalls.filter((s) => s.finalState === 'HUMAN_HANDOFF').length} />
      </div>

      {/* Active calls */}
      <div className="rounded-xl border border-outline-variant bg-surface-container-lowest shadow-sm overflow-hidden">
        <div className="flex items-center justify-between px-md py-sm border-b border-outline-variant">
          <span className="font-label-caps text-label-caps text-on-surface-variant">ACTIVE CALLS</span>
          {activeCalls.length > 0 && (
            <span className="rounded-full bg-primary px-sm py-xs font-label-caps text-label-caps text-on-primary">
              {activeCalls.length} live
            </span>
          )}
        </div>

        {error !== null && (
          <div className="m-md rounded-lg bg-error-container p-sm">
            <p className="font-caption text-caption text-on-error-container">{error}</p>
          </div>
        )}

        {!loading && error === null && activeCalls.length === 0 && (
          <div className="flex flex-col items-center justify-center py-xl text-center">
            <span className="material-symbols-outlined text-[48px] text-outline mb-sm">phone_disabled</span>
            <p className="font-body-md text-body-md text-on-surface-variant">No active calls</p>
            <p className="font-caption text-caption text-outline">Calls appear here when the agent is live.</p>
          </div>
        )}

        {activeCalls.length > 0 && (
          <div className="divide-y divide-outline-variant">
            {activeCalls.map((s) => (
              <Link
                key={s.sessionId}
                href={`/sessions/${s.sessionId}`}
                className="flex items-center justify-between px-md py-sm hover:bg-surface-container-low transition-colors"
              >
                <div className="flex items-center gap-sm">
                  {/* live pulse */}
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-secondary opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-secondary" />
                  </span>
                  <p className="font-label-caps text-label-caps text-on-surface">
                    {s.sessionId.slice(0, 8).toUpperCase()}
                  </p>
                </div>
                <StateBadge state={s.finalState} />
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
