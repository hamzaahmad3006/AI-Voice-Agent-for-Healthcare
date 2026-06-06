import StateBadge from './StateBadge';
import type { TurnLog as TurnLogEntry } from '@/types/session';

interface Props {
  turns: TurnLogEntry[];
}

export default function TurnLog({ turns }: Props): JSX.Element {
  if (turns.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-lg text-center">
        <span className="material-symbols-outlined text-[40px] text-outline">chat_bubble_outline</span>
        <p className="mt-xs font-body-md text-body-md text-on-surface-variant">No turns recorded.</p>
      </div>
    );
  }

  return (
    <ol className="flex flex-col gap-sm">
      {turns.map((turn) => (
        <li key={turn.n} className="rounded-xl border border-outline-variant bg-surface-container-low p-md">
          <div className="mb-xs flex items-center gap-xs">
            <span className="font-label-caps text-label-caps text-outline">#{turn.n}</span>
            <StateBadge state={turn.state} />
            {turn.latencyMs !== null && (
              <span className="ml-auto font-caption text-caption text-outline">{turn.latencyMs} ms</span>
            )}
          </div>

          {/* Agent */}
          <div className="flex gap-xs mt-xs">
            <span className="flex-shrink-0 rounded bg-primary-fixed px-xs py-xs font-label-caps text-label-caps text-on-primary-fixed-variant">
              AGENT
            </span>
            <p className="font-body-md text-body-md text-on-surface">{turn.agentText}</p>
          </div>

          {/* Caller */}
          {turn.callerText !== null && (
            <div className="flex gap-xs mt-xs">
              <span className="flex-shrink-0 rounded bg-surface-container-high px-xs py-xs font-label-caps text-label-caps text-on-surface-variant">
                CALLER
              </span>
              <p className="font-body-md text-body-md text-on-surface-variant">{turn.callerText}</p>
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}
