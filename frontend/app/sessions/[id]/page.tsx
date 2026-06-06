'use client';

import { use } from 'react';
import Link from 'next/link';

import StateBadge from '@/components/StateBadge';
import TurnLog from '@/components/TurnLog';
import { useSessionDetail } from '@/hooks/useSessionDetail';

interface Props {
  params: Promise<{ id: string }>;
}

export default function SessionDetailPage({ params }: Props): JSX.Element {
  const { id } = use(params);
  const { session, loading, error } = useSessionDetail(id);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-gray-400">Loading session…</p>
      </div>
    );
  }

  if (error !== null || session === null) {
    return (
      <div className="p-8">
        <Link href="/sessions" className="mb-4 inline-flex items-center gap-1 text-sm text-blue-600 hover:underline">
          ← Back to Sessions
        </Link>
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error ?? 'Session not found.'}
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Breadcrumb */}
      <Link href="/sessions" className="mb-4 inline-flex items-center gap-1 text-sm text-blue-600 hover:underline">
        ← Sessions
      </Link>

      {/* Header */}
      <div className="mb-6 flex items-center gap-3">
        <h2 className="font-mono text-2xl font-bold text-gray-900">
          {session.sessionId.slice(0, 8).toUpperCase()}
        </h2>
        <StateBadge state={session.finalState} />
        {session.outcome !== null && (
          <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
            {session.outcome}
          </span>
        )}
      </div>

      {/* Meta grid */}
      <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: 'Room',      value: session.roomName },
          { label: 'Started',   value: new Date(session.startedAt).toLocaleString() },
          { label: 'Ended',     value: session.endedAt !== null ? new Date(session.endedAt).toLocaleString() : '—' },
          { label: 'Patient',   value: session.patientId ?? '—' },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium text-gray-400">{label}</p>
            <p className="mt-1 truncate text-sm font-semibold text-gray-900">{value}</p>
          </div>
        ))}
      </div>

      {/* Tool calls */}
      {session.toolCalls.length > 0 && (
        <section className="mb-8">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
            Tool Calls
          </h3>
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-100">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Tool</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Status</th>
                  <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {session.toolCalls.map((tc, i) => (
                  <tr key={i}>
                    <td className="px-4 py-2 font-mono text-sm text-gray-800">{tc.tool}</td>
                    <td className="px-4 py-2 text-sm">
                      <span className={tc.status === 'ok' ? 'text-emerald-600' : 'text-red-600'}>
                        {tc.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-500">{tc.latencyMs} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Turn log */}
      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Conversation ({session.turns.length} turns)
        </h3>
        <TurnLog turns={session.turns} />
      </section>
    </div>
  );
}
