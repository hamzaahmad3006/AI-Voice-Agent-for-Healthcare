'use client';

import CallCard from '@/components/CallCard';
import MetricWidget from '@/components/MetricWidget';
import { useLiveCall } from '@/hooks/useLiveCall';

export default function DashboardPage(): JSX.Element {
  const { activeCalls, totalToday, bookedToday, loading, error } = useLiveCall();

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
        <p className="mt-1 text-sm text-gray-500">Real-time call activity and booking metrics.</p>
      </div>

      {/* Metrics row */}
      <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricWidget
          label="Active Calls"
          value={loading ? '—' : activeCalls.length}
          accent="blue"
          sub="Live right now"
        />
        <MetricWidget
          label="Total Sessions"
          value={loading ? '—' : totalToday}
          accent="gray"
          sub="All in Redis"
        />
        <MetricWidget
          label="Bookings"
          value={loading ? '—' : bookedToday}
          accent="green"
          sub="Confirmed"
        />
        <MetricWidget
          label="Handoffs"
          value={loading ? '—' : activeCalls.filter((s) => s.finalState === 'HUMAN_HANDOFF').length}
          accent="amber"
          sub="Transferred"
        />
      </div>

      {/* Active calls */}
      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Active Calls
        </h3>

        {error !== null && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            Could not load sessions: {error}
          </div>
        )}

        {!loading && error === null && activeCalls.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-gray-300 bg-white py-16 text-center">
            <p className="text-2xl">📞</p>
            <p className="mt-2 text-sm font-medium text-gray-500">No active calls</p>
            <p className="text-xs text-gray-400">Calls will appear here when the agent is live.</p>
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {activeCalls.map((session) => (
            <CallCard key={session.sessionId} session={session} />
          ))}
        </div>
      </section>
    </div>
  );
}
