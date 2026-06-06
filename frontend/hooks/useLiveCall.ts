'use client';

import { useSessions } from './useSessions';
import type { SessionListItem } from '@/types/session';

const ACTIVE_STATES: SessionListItem['finalState'][] = [
  'GREETING',
  'CONSENT_DATA',
  'IDENTIFY',
  'RETRIEVE_OR_CREATE',
  'VISIT_INTAKE',
  'SLOT_SEARCH',
  'INSURANCE_CHECK',
  'CONFIRM',
  'BOOK',
];

export interface LiveCallState {
  activeCalls: SessionListItem[];
  totalToday: number;
  bookedToday: number;
  loading: boolean;
  error: string | null;
}

export function useLiveCall(): LiveCallState {
  const { sessions, loading, error } = useSessions();

  const activeCalls = sessions.filter((s) =>
    ACTIVE_STATES.includes(s.finalState),
  );

  const bookedToday = sessions.filter((s) => s.outcome === 'booked').length;

  return {
    activeCalls,
    totalToday: sessions.length,
    bookedToday,
    loading,
    error,
  };
}
