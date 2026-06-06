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
      <div className="flex items-center justify-center py-xl">
        <p className="font-body-md text-body-md text-on-surface-variant">Loading session…</p>
      </div>
    );
  }

  if (error !== null || session === null) {
    return (
      <div>
        <Link href="/sessions" className="mb-md inline-flex items-center gap-xs font-label-caps text-label-caps text-primary hover:underline">
          <span className="material-symbols-outlined text-[16px]">arrow_back</span>
          SESSIONS
        </Link>
        <div className="rounded-lg bg-error-container px-md py-sm">
          <p className="font-body-md text-body-md text-on-error-container">{error ?? 'Session not found.'}</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Breadcrumb */}
      <Link href="/sessions" className="mb-md inline-flex items-center gap-xs font-label-caps text-label-caps text-on-surface-variant hover:text-primary transition-colors">
        <span className="material-symbols-outlined text-[16px]">arrow_back</span>
        SESSIONS
      </Link>

      {/* Header */}
      <div className="mb-md flex flex-wrap items-center gap-sm">
        <h2 className="font-headline-md text-headline-md text-on-surface font-mono">
          {session.sessionId.slice(0, 8).toUpperCase()}
        </h2>
        <StateBadge state={session.finalState} />
        {session.outcome !== null && (
          <span className="rounded-full bg-secondary-container px-sm py-xs font-label-caps text-label-caps text-on-secondary-container">
            {session.outcome.toUpperCase()}
          </span>
        )}
      </div>

      {/* Meta cards */}
      <div className="mb-md grid grid-cols-2 gap-md md:grid-cols-4">
        {[
          { icon: 'meeting_room', label: 'ROOM',    value: session.roomName },
          { icon: 'schedule',     label: 'STARTED', value: new Date(session.startedAt).toLocaleString() },
          { icon: 'event',        label: 'ENDED',   value: session.endedAt !== null ? new Date(session.endedAt).toLocaleString() : '—' },
          { icon: 'person',       label: 'PATIENT', value: session.patientId ?? '—' },
        ].map(({ icon, label, value }) => (
          <div key={label} className="rounded-xl border border-outline-variant bg-surface-container-lowest p-sm shadow-sm">
            <div className="flex items-center gap-xs mb-xs">
              <span className="material-symbols-outlined text-[16px] text-on-surface-variant">{icon}</span>
              <p className="font-label-caps text-label-caps text-on-surface-variant">{label}</p>
            </div>
            <p className="font-body-md text-body-md text-on-surface truncate">{value}</p>
          </div>
        ))}
      </div>

      {/* Tool calls */}
      {session.toolCalls.length > 0 && (
        <div className="mb-md rounded-xl border border-outline-variant bg-surface-container-lowest shadow-sm overflow-hidden">
          <div className="border-b border-outline-variant px-md py-sm">
            <span className="font-label-caps text-label-caps text-on-surface-variant">TOOL CALLS</span>
          </div>
          <table className="min-w-full">
            <thead>
              <tr className="bg-surface-container-low">
                <th className="px-md py-xs text-left font-label-caps text-label-caps text-on-surface-variant">TOOL</th>
                <th className="px-md py-xs text-left font-label-caps text-label-caps text-on-surface-variant">STATUS</th>
                <th className="px-md py-xs text-left font-label-caps text-label-caps text-on-surface-variant">LATENCY</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant">
              {session.toolCalls.map((tc, i) => (
                <tr key={i}>
                  <td className="px-md py-xs font-label-caps text-label-caps text-on-surface">{tc.tool}</td>
                  <td className="px-md py-xs">
                    <span className={`font-label-caps text-label-caps ${tc.status === 'ok' ? 'text-secondary' : 'text-error'}`}>
                      {tc.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-md py-xs font-caption text-caption text-on-surface-variant">{tc.latencyMs} ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Turn log */}
      <div className="rounded-xl border border-outline-variant bg-surface-container-lowest shadow-sm overflow-hidden">
        <div className="border-b border-outline-variant px-md py-sm flex items-center justify-between">
          <span className="font-label-caps text-label-caps text-on-surface-variant">CONVERSATION</span>
          <span className="font-label-caps text-label-caps text-on-surface-variant">{session.turns.length} TURNS</span>
        </div>
        <div className="p-md">
          <TurnLog turns={session.turns} />
        </div>
      </div>
    </div>
  );
}
