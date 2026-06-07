export interface ChatMessage {
  role: 'ai' | 'user';
  text: string;
  time: string;
}

export interface SessionStartResponse {
  session_id: string;
  greeting: string;
}

export interface TurnResponse {
  response_text: string;
  state: string;
  session_ended: boolean;
}
