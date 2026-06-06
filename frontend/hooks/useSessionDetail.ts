'use client';

import { useCallback, useEffect, useState } from 'react';

import { fetchSessionDetail } from '@/services/sessionsService';
import type { SessionDetailState } from '@/types/session';

export function useSessionDetail(sessionId: string): SessionDetailState {
  const [state, setState] = useState<SessionDetailState>({
    session: null,
    loading: true,
    error: null,
  });

  const load = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const session = await fetchSessionDetail(sessionId);
      setState({ session, loading: false, error: null });
    } catch (err) {
      setState({
        session: null,
        loading: false,
        error: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  }, [sessionId]);

  useEffect(() => { void load(); }, [load]);

  return state;
}
