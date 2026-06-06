'use client';

import Link from 'next/link';

import StateBadge from '@/components/StateBadge';
import { useSessions } from '@/hooks/useSessions';

const OUTCOME_STYLES: Record<string, string> = {
  booked:      'text-emerald-600',
  no_booking:  'text-gray-500',
  transferred: 'text-amber-600',
  error:       'text-red-600',
};

export default function SessionsPage(): JSX.Element {
  const { sessions, loading, error, refresh } = useSessions();

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Sessions</h2>
          <p className="mt-1 text-sm text-gray-500">All sessions currently live in Redis.</p>
        </div>
        <button
          onClick={refresh}
          className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
        >
          Refresh
        </button>
      </div>

      {error !== null && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && (
        <div className="flex justify-center py-16">
          <span className="text-sm text-gray-400">Loading…</span>
        </div>
      )}

      {!loading && sessions.length === 0 && error === null && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-gray-300 bg-white py-20 text-center">
          <p className="text-2xl">📋</p>
          <p className="mt-2 text-sm font-medium text-gray-500">No sessions in Redis</p>
        </div>
      )}

      {sessions.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Session ID
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  State
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Outcome
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Started
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sessions.map((s) => (
                <tr key={s.sessionId} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link
                      href={`/sessions/${s.sessionId}`}
                      className="font-mono text-sm font-medium text-blue-600 hover:underline"
                    >
                      {s.sessionId.slice(0, 8).toUpperCase()}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <StateBadge state={s.finalState} />
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-sm font-medium ${s.outcome !== null ? (OUTCOME_STYLES[s.outcome] ?? 'text-gray-500') : 'text-gray-400'}`}
                    >
                      {s.outcome ?? 'in progress'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
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
