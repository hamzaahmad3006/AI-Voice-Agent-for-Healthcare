'use client';

import { useCallback, useEffect, useState } from 'react';

import { fetchSessions } from '@/services/sessionsService';
import type { SessionListItem, SessionListState } from '@/types/session';

const POLL_INTERVAL_MS = 5000;

export function useSessions(): SessionListState & { refresh: () => void } {
  const [state, setState] = useState<SessionListState>({
    sessions: [],
    loading: true,
    error: null,
  });

  const load = useCallback(async () => {
    try {
      const sessions: SessionListItem[] = await fetchSessions();
      setState({ sessions, loading: false, error: null });
    } catch (err) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : 'Unknown error',
      }));
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => { void load(); }, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [load]);

  return { ...state, refresh: load };
}
