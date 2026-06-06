import type { SessionListItem, SessionLog } from '@/types/session';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// Snake-case keys from the backend are mapped to camelCase here.
// Only the fields we actually use are mapped — no dynamic key transforms.

function toListItem(raw: Record<string, unknown>): SessionListItem {
  return {
    sessionId: raw['session_id'] as string,
    startedAt: raw['started_at'] as string,
    endedAt: (raw['ended_at'] as string | null) ?? null,
    outcome: (raw['outcome'] as SessionListItem['outcome']) ?? null,
    finalState: raw['final_state'] as SessionListItem['finalState'],
    patientId: (raw['patient_id'] as string | null) ?? null,
  };
}

function toSessionLog(raw: Record<string, unknown>): SessionLog {
  const turns = (raw['turns'] as Array<Record<string, unknown>> | undefined) ?? [];
  const toolCalls =
    (raw['tool_calls'] as Array<Record<string, unknown>> | undefined) ?? [];
  const consentEvents =
    (raw['consent_events'] as Array<Record<string, unknown>> | undefined) ?? [];

  return {
    sessionId: raw['session_id'] as string,
    roomName: raw['room_name'] as string,
    callerNumber: raw['caller_number'] as string,
    patientId: (raw['patient_id'] as string | null) ?? null,
    startedAt: raw['started_at'] as string,
    endedAt: (raw['ended_at'] as string | null) ?? null,
    outcome: (raw['outcome'] as SessionLog['outcome']) ?? null,
    finalState: raw['final_state'] as SessionLog['finalState'],
    consentEvents: consentEvents.map((e) => ({
      type: e['type'] as SessionLog['consentEvents'][0]['type'],
      value: e['value'] as SessionLog['consentEvents'][0]['value'],
      at: e['at'] as string,
      transcriptSnippet: e['transcript_snippet'] as string,
      sessionId: e['session_id'] as string,
    })),
    turns: turns.map((t) => ({
      n: t['n'] as number,
      state: t['state'] as SessionLog['finalState'],
      agentText: t['agent_text'] as string,
      callerText: (t['caller_text'] as string | null) ?? null,
      latencyMs: (t['latency_ms'] as number | null) ?? null,
    })),
    toolCalls: toolCalls.map((tc) => ({
      tool: tc['tool'] as string,
      status: tc['status'] as 'ok' | 'error' | 'timeout',
      latencyMs: tc['latency_ms'] as number,
      errorMessage: (tc['error_message'] as string | null) ?? null,
    })),
    phiTags: (raw['phi_tags'] as string[]) ?? [],
  };
}

export async function fetchSessions(): Promise<SessionListItem[]> {
  const res = await fetch(`${API}/sessions`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`GET /sessions failed: ${res.status}`);
  const raw = (await res.json()) as Array<Record<string, unknown>>;
  return raw.map(toListItem);
}

export async function fetchSessionDetail(id: string): Promise<SessionLog> {
  const res = await fetch(`${API}/sessions/${id}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`GET /sessions/${id} failed: ${res.status}`);
  const raw = (await res.json()) as Record<string, unknown>;
  return toSessionLog(raw);
}
