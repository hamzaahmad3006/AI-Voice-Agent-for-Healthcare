import Link from 'next/link';

import StateBadge from './StateBadge';
import type { SessionListItem } from '@/types/session';

interface Props {
  session: SessionListItem;
}

function elapsed(startedAt: string): string {
  const diff = Date.now() - new Date(startedAt).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  return `${m}m ${s % 60}s`;
}

export default function CallCard({ session }: Props): JSX.Element {
  return (
    <Link
      href={`/sessions/${session.sessionId}`}
      className="flex items-center justify-between rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition hover:shadow-md"
    >
      <div className="flex items-center gap-3">
        {/* Live pulse indicator */}
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
        </span>
        <div>
          <p className="text-sm font-semibold text-gray-900">
            {session.sessionId.slice(0, 8).toUpperCase()}
          </p>
          <p className="text-xs text-gray-400">
            {elapsed(session.startedAt)} ago
          </p>
        </div>
      </div>
      <StateBadge state={session.finalState} />
    </Link>
  );
}
