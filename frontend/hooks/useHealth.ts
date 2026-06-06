'use client';

import { useCallback, useEffect, useState } from 'react';

import { fetchHealth } from '@/services/healthService';
import type { HealthState } from '@/types/health';

const POLL_INTERVAL_MS = 15000;

export function useHealth(): HealthState {
  const [state, setState] = useState<HealthState>({
    health: null,
    loading: true,
    error: null,
  });

  const load = useCallback(async () => {
    try {
      const health = await fetchHealth();
      setState({ health, loading: false, error: null });
    } catch (err) {
      setState({
        health: null,
        loading: false,
        error: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => { void load(); }, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [load]);

  return state;
}
