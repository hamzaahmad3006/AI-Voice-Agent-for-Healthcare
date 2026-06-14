import type { SessionStartResponse, TurnResponse } from '@/types/conversation';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function startSession(): Promise<SessionStartResponse> {
  const res = await fetch(`${API_BASE}/sessions`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to start session: ${res.status}`);
  return res.json() as Promise<SessionStartResponse>;
}

export async function sendTurn(
  sessionId: string,
  text: string,
): Promise<TurnResponse> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/turn`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(`Turn failed: ${res.status}`);
  return res.json() as Promise<TurnResponse>;
}
