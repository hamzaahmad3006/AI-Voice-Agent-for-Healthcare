'use client';

import Link from 'next/link';

import StateBadge from '@/components/StateBadge';
import { useSessions } from '@/hooks/useSessions';

const OUTCOME_COLOR: Record<string, string> = {
  booked:      'text-secondary',
  no_booking:  'text-on-surface-variant',
  transferred: 'text-tertiary',
  error:       'text-error',
};

export default function SessionsPage(): JSX.Element {
  const { sessions, loading, error, refresh } = useSessions();

  return (
    <div>
      <div className="mb-md flex items-center justify-between">
        <div>
          <h2 className="font-headline-md text-headline-md text-on-surface">Sessions</h2>
          <p className="font-body-md text-body-md text-on-surface-variant mt-xs">
            All sessions currently live in Redis.
          </p>
        </div>
        <button
          onClick={refresh}
          className="flex items-center gap-xs rounded-lg border border-outline-variant bg-surface-container-lowest px-sm py-xs font-label-caps text-label-caps text-on-surface-variant shadow-sm hover:bg-surface-container-low transition-colors"
        >
          <span className="material-symbols-outlined text-[16px]">refresh</span>
          REFRESH
        </button>
      </div>

      {error !== null && (
        <div className="mb-md rounded-lg bg-error-container px-md py-sm">
          <p className="font-caption text-caption text-on-error-container">{error}</p>
        </div>
      )}

      {loading && (
        <div className="flex justify-center py-xl">
          <p className="font-body-md text-body-md text-on-surface-variant">Loading…</p>
        </div>
      )}

      {!loading && sessions.length === 0 && error === null && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-outline-variant bg-surface-container-lowest py-xl text-center">
          <span className="material-symbols-outlined text-[48px] text-outline mb-sm">inbox</span>
          <p className="font-body-md text-body-md text-on-surface-variant">No sessions in Redis</p>
        </div>
      )}

      {sessions.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest shadow-sm">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-outline-variant bg-surface-container-low">
                <th className="px-md py-sm text-left font-label-caps text-label-caps text-on-surface-variant">SESSION</th>
                <th className="px-md py-sm text-left font-label-caps text-label-caps text-on-surface-variant">STATE</th>
                <th className="px-md py-sm text-left font-label-caps text-label-caps text-on-surface-variant">OUTCOME</th>
                <th className="px-md py-sm text-left font-label-caps text-label-caps text-on-surface-variant">STARTED</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant">
              {sessions.map((s) => (
                <tr key={s.sessionId} className="hover:bg-surface-container-low transition-colors">
                  <td className="px-md py-sm">
                    <Link
                      href={`/sessions/${s.sessionId}`}
                      className="font-label-caps text-label-caps text-primary hover:underline"
                    >
                      {s.sessionId.slice(0, 8).toUpperCase()}
                    </Link>
                  </td>
                  <td className="px-md py-sm">
                    <StateBadge state={s.finalState} />
                  </td>
                  <td className="px-md py-sm">
                    <span className={`font-caption text-caption ${s.outcome !== null ? (OUTCOME_COLOR[s.outcome] ?? 'text-on-surface-variant') : 'text-outline'}`}>
                      {s.outcome ?? 'in progress'}
                    </span>
                  </td>
                  <td className="px-md py-sm font-caption text-caption text-on-surface-variant">
                    {new Date(s.startedAt).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
