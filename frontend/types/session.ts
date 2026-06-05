// Mirrors backend/models/fsm_state.py FSMState and backend/models/session_log.py

export type FSMState =
  | 'GREETING'
  | 'CONSENT_DATA'
  | 'IDENTIFY'
  | 'RETRIEVE_OR_CREATE'
  | 'VISIT_INTAKE'
  | 'SLOT_SEARCH'
  | 'INSURANCE_CHECK'
  | 'CONFIRM'
  | 'BOOK'
  | 'CLOSING'
  | 'HUMAN_HANDOFF'
  | 'ERROR_FALLBACK';

export type SessionOutcome = 'booked' | 'no_booking' | 'transferred' | 'error';

export type ConsentType = 'data_processing' | 'booking';

export type ConsentValue = 'yes' | 'no' | 'unclear';

export interface ConsentEvent {
  type: ConsentType;
  value: ConsentValue;
  at: string; // ISO 8601
  transcriptSnippet: string;
  sessionId: string;
}

export interface TurnLog {
  n: number;
  state: FSMState;
  agentText: string;
  callerText: string | null;
  latencyMs: number | null;
}

export interface ToolCallLog {
  tool: string;
  status: 'ok' | 'error' | 'timeout';
  latencyMs: number;
  errorMessage: string | null;
}

export interface SessionLog {
  sessionId: string;
  roomName: string;
  callerNumber: string;
  patientId: string | null;
  startedAt: string; // ISO 8601
  endedAt: string | null; // ISO 8601
  outcome: SessionOutcome | null;
  finalState: FSMState;
  consentEvents: ConsentEvent[];
  turns: TurnLog[];
  toolCalls: ToolCallLog[];
  phiTags: string[];
}

export interface SessionListItem {
  sessionId: string;
  startedAt: string;
  endedAt: string | null;
  outcome: SessionOutcome | null;
  finalState: FSMState;
  patientId: string | null;
}

export interface SessionListState {
  sessions: SessionListItem[];
  loading: boolean;
  error: string | null;
}

export interface SessionDetailState {
  session: SessionLog | null;
  loading: boolean;
  error: string | null;
}
