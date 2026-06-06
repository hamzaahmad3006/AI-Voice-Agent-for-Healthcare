import StateBadge from './StateBadge';
import type { TurnLog as TurnLogEntry } from '@/types/session';

interface Props {
  turns: TurnLogEntry[];
}

export default function TurnLog({ turns }: Props): JSX.Element {
  if (turns.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-gray-400">No turns recorded.</p>
    );
  }

  return (
    <ol className="space-y-3">
      {turns.map((turn) => (
        <li key={turn.n} className="rounded-xl border border-gray-100 bg-gray-50 p-4">
          <div className="mb-2 flex items-center gap-2">
            <span className="text-xs font-medium text-gray-400">#{turn.n}</span>
            <StateBadge state={turn.state} />
            {turn.latencyMs !== null && (
              <span className="ml-auto text-xs text-gray-400">
                {turn.latencyMs} ms
              </span>
            )}
          </div>
          {/* Agent utterance */}
          <div className="flex gap-2">
            <span className="mt-0.5 flex-shrink-0 rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-blue-700">
              Agent
            </span>
            <p className="text-sm text-gray-800">{turn.agentText}</p>
          </div>
          {/* Caller utterance */}
          {turn.callerText !== null && (
            <div className="mt-2 flex gap-2">
              <span className="mt-0.5 flex-shrink-0 rounded bg-gray-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-gray-600">
                Caller
              </span>
              <p className="text-sm text-gray-700">{turn.callerText}</p>
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}
