'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { sendTurn, startSession } from '@/services/conversationService';
import type { ChatMessage } from '@/types/conversation';

const BAR_COUNT = 40;

type CallStatus = 'connecting' | 'idle' | 'listening' | 'processing' | 'speaking' | 'ended';

interface SpeechRecognitionAlternative {
  readonly transcript: string;
}
interface SpeechRecognitionResult {
  readonly [index: number]: SpeechRecognitionAlternative | undefined;
}
interface SpeechRecognitionResultList {
  readonly [index: number]: SpeechRecognitionResult | undefined;
}
interface SpeechRecognitionEvent extends Event {
  readonly results: SpeechRecognitionResultList;
}
interface SpeechRecognitionErrorEvent extends Event {
  readonly error: string;
}
interface SpeechRecognitionInstance {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onstart: ((ev: Event) => void) | null;
  onend: ((ev: Event) => void) | null;
  onresult: ((ev: SpeechRecognitionEvent) => void) | null;
  onerror: ((ev: SpeechRecognitionErrorEvent) => void) | null;
  start(): void;
  abort(): void;
}
type SpeechRecognitionCtor = new () => SpeechRecognitionInstance;

function getSpeechRecognitionCtor(): SpeechRecognitionCtor | undefined {
  if (typeof window === 'undefined') return undefined;
  const w = window as Window &
    typeof globalThis & {
      SpeechRecognition?: SpeechRecognitionCtor;
      webkitSpeechRecognition?: SpeechRecognitionCtor;
    };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition;
}

const STATUS_LABEL: Record<CallStatus, string> = {
  connecting: 'Connecting...',
  idle: 'Tap mic to speak',
  listening: 'Listening...',
  processing: 'Processing...',
  speaking: 'AI Speaking...',
  ended: 'Call Ended',
};

export default function CallPage(): JSX.Element {
  const [status, setStatus] = useState<CallStatus>('connecting');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [seconds, setSeconds] = useState(0);
  const [speechSupported, setSpeechSupported] = useState(true);

  const secondsRef = useRef(0);
  const sessionIdRef = useRef<string | null>(null);
  const sessionEndedRef = useRef(false);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const waveformRef = useRef<HTMLDivElement>(null);
  const barsRef = useRef<HTMLDivElement[]>([]);
  const rafRef = useRef<number | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const chatRef = useRef<HTMLDivElement>(null);

  // ── Timer ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    const id = setInterval(() => {
      secondsRef.current += 1;
      setSeconds(secondsRef.current);
    }, 1000);
    return (): void => clearInterval(id);
  }, []);

  // ── Waveform ───────────────────────────────────────────────────────────────
  useEffect(() => {
    const el = waveformRef.current;
    if (el === null) return;
    el.innerHTML = '';
    barsRef.current = [];
    for (let i = 0; i < BAR_COUNT; i++) {
      const bar = document.createElement('div');
      bar.className = 'wave-bar w-1.5 bg-primary rounded-full opacity-60';
      bar.style.height = `${Math.random() * 60 + 10}%`;
      el.appendChild(bar);
      barsRef.current.push(bar);
    }
    function animate(): void {
      barsRef.current.forEach((bar) => {
        const h = Math.random() * 80 + 10;
        bar.style.height = `${h}%`;
        if (h > 60) bar.classList.replace('bg-primary', 'bg-secondary');
        else bar.classList.replace('bg-secondary', 'bg-primary');
      });
      timeoutRef.current = setTimeout(() => {
        rafRef.current = requestAnimationFrame(animate);
      }, 150);
    }
    rafRef.current = requestAnimationFrame(animate);
    return (): void => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      if (timeoutRef.current !== null) clearTimeout(timeoutRef.current);
    };
  }, []);

  // ── Auto-scroll ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [messages]);

  // ── Stable function refs (updated every render, called only in async callbacks)
  // Allows mutual recursion between speak ↔ listen without circular useCallback deps.

  const addMessageRef = useRef<(role: 'ai' | 'user', text: string) => void>(() => {});
  addMessageRef.current = (role: 'ai' | 'user', text: string): void => {
    const s = secondsRef.current;
    const time = `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`;
    setMessages((prev) => [...prev, { role, text, time }]);
  };

  const listenRef = useRef<() => void>(() => {});

  const speakRef = useRef<(text: string, autoListen?: boolean) => void>(() => {});
  speakRef.current = (text: string, autoListen = true): void => {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    setStatus('speaking');

    let fired = false;
    const onDone = (): void => {
      if (fired) return;
      fired = true;
      clearTimeout(fallback);
      setStatus('idle');
      if (autoListen && !sessionEndedRef.current) {
        // Brief pause so the mic doesn't pick up the TTS echo
        setTimeout(() => listenRef.current(), 700);
      }
    };

    // Safety fallback: ~80 ms per character + 2 s buffer
    const fallback = setTimeout(onDone, text.length * 80 + 2000);
    utterance.onend = onDone;
    utterance.onerror = (): void => {
      if (!fired) { fired = true; clearTimeout(fallback); setStatus('idle'); }
    };
    window.speechSynthesis.speak(utterance);
  };

  listenRef.current = (): void => {
    const sid = sessionIdRef.current;
    if (!sid || sessionEndedRef.current) return;

    const SpeechRec = getSpeechRecognitionCtor();
    if (!SpeechRec) return;

    recognitionRef.current?.abort();
    const recognition = new SpeechRec();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    recognitionRef.current = recognition;

    recognition.onstart = (): void => setStatus('listening');
    recognition.onend = (): void => {
      setStatus((prev) => (prev === 'listening' ? 'idle' : prev));
    };

    recognition.onresult = (event: SpeechRecognitionEvent): void => {
      const alt = event.results[0]?.[0];
      if (!alt) return;

      const text = alt.transcript;
      addMessageRef.current('user', text);
      setStatus('processing');

      sendTurn(sid, text)
        .then(({ response_text, session_ended }) => {
          addMessageRef.current('ai', response_text);
          if (session_ended) {
            sessionEndedRef.current = true;
            setStatus('ended');
            speakRef.current(response_text, false); // speak closing, don't auto-listen
          } else {
            speakRef.current(response_text); // speak then auto-listen
          }
        })
        .catch(() => {
          addMessageRef.current('ai', 'Connection error. Please tap the mic and try again.');
          setStatus('idle');
        });
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent): void => {
      if (event.error !== 'no-speech') setStatus('idle');
    };

    recognition.start();
  };

  // ── Initialize session on mount ────────────────────────────────────────────
  const initializedRef = useRef(false);

  useEffect(() => {
    // Guard against React StrictMode double-invoke in development
    if (initializedRef.current) return;
    initializedRef.current = true;

    if (!getSpeechRecognitionCtor()) setSpeechSupported(false);

    startSession()
      .then(({ session_id, greeting }) => {
        sessionIdRef.current = session_id;
        addMessageRef.current('ai', greeting);
        speakRef.current(greeting);
      })
      .catch(() => {
        addMessageRef.current('ai', 'Unable to connect to VocalHealth AI. Please check the backend is running.');
        setStatus('ended');
      });
  }, []); // refs are stable — no deps needed

  // ── Manual mic button ──────────────────────────────────────────────────────
  const handleMicClick = (): void => {
    if (sessionEndedRef.current || status === 'processing') return;
    if (status === 'listening') {
      recognitionRef.current?.abort();
      setStatus('idle');
      return;
    }
    window.speechSynthesis.cancel();
    listenRef.current();
  };

  const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
  const secs = (seconds % 60).toString().padStart(2, '0');
  const micActive = status === 'listening';
  const micDisabled = !speechSupported || status === 'ended' || status === 'processing';

  return (
    <>
      {/* Top Nav */}
      <header className="fixed top-0 left-0 w-full z-50 flex justify-between items-center px-margin-mobile md:px-margin-desktop h-16 bg-surface/70 backdrop-blur-xl shadow-sm">
        <div className="flex items-center gap-base">
          <span className="material-symbols-outlined text-primary text-headline-md fill-icon">health_and_safety</span>
          <span className="font-headline-md text-headline-md font-bold text-primary">VocalHealth AI</span>
        </div>
        <div className="flex items-center gap-md">
          <button className="material-symbols-outlined text-on-surface-variant hover:text-primary transition-colors duration-300 ease-out active:scale-95">
            account_circle
          </button>
          <button className="material-symbols-outlined text-on-surface-variant hover:text-primary transition-colors duration-300 ease-out active:scale-95">
            settings
          </button>
        </div>
      </header>

      {/* Main */}
      <main className="flex-grow pt-24 pb-12 px-margin-mobile md:px-margin-desktop flex flex-col md:flex-row gap-lg">

        {/* ── Voice Interface ─────────────────────────────────────────────── */}
        <section className="flex-grow flex flex-col items-center justify-center relative bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant p-lg overflow-hidden">

          <div className="absolute inset-0 pointer-events-none opacity-20 overflow-hidden">
            <div className="absolute -top-1/4 -left-1/4 w-1/2 h-1/2 bg-primary rounded-full blur-[120px] animate-pulse-glow" />
            <div className="absolute -bottom-1/4 -right-1/4 w-1/2 h-1/2 bg-secondary rounded-full blur-[120px] animate-pulse-glow" style={{ animationDelay: '1s' }} />
          </div>

          {/* AI Avatar */}
          <div className="flex flex-col items-center gap-sm mb-xl z-10">
            <div className={`w-24 h-24 rounded-full bg-primary-fixed-dim flex items-center justify-center shadow-lg border-4 transition-all duration-300 ${
              micActive ? 'border-secondary animate-pulse' :
              status === 'speaking' ? 'border-primary animate-pulse' :
              'border-surface-container-highest'
            }`}>
              <span className="material-symbols-outlined text-primary text-[48px] fill-icon">neurology</span>
            </div>
            <h1 className="font-headline-md text-headline-md text-primary">Aura AI</h1>
            <p className={`font-label-caps text-label-caps tracking-widest uppercase transition-colors ${
              micActive ? 'text-secondary' :
              status === 'processing' ? 'text-tertiary' :
              status === 'speaking' ? 'text-primary' :
              status === 'ended' ? 'text-error' :
              'text-on-surface-variant'
            }`}>
              {STATUS_LABEL[status]}
            </p>
          </div>

          {/* Waveform */}
          <div
            ref={waveformRef}
            className="flex items-center justify-center gap-1 h-32 mb-xl z-10 w-full max-w-lg"
          />

          {!speechSupported && (
            <div className="mb-lg z-10 px-md py-sm bg-error-container text-on-error-container rounded-lg font-body-md text-center max-w-sm">
              Speech recognition is not available. Please use Chrome or Edge.
            </div>
          )}

          {/* Controls */}
          <div className="flex flex-col items-center gap-md z-10 w-full max-w-md">
            <div className="font-label-caps text-label-caps text-primary tracking-widest mb-base">
              {mins}:{secs}
            </div>
            <div className="flex items-center gap-lg">
              {/* Mic */}
              <button
                onClick={handleMicClick}
                disabled={micDisabled}
                className={`w-16 h-16 rounded-full flex items-center justify-center border transition-all duration-300 group ${
                  micActive
                    ? 'bg-secondary border-secondary'
                    : 'border-outline-variant hover:bg-surface-container-high'
                } disabled:opacity-40 disabled:cursor-not-allowed`}
              >
                <span className={`material-symbols-outlined group-active:scale-90 transition-colors ${
                  micActive ? 'text-on-secondary' : 'text-on-surface-variant'
                }`}>
                  {micActive ? 'mic' : 'mic_none'}
                </span>
              </button>

              {/* End call */}
              <Link
                href="/confirmation"
                onClick={() => {
                  window.speechSynthesis.cancel();
                  recognitionRef.current?.abort();
                }}
                className="w-20 h-20 rounded-full bg-error text-on-error flex items-center justify-center shadow-lg shadow-error/20 hover:scale-105 active:scale-95 transition-all duration-300"
              >
                <span className="material-symbols-outlined text-[32px] fill-icon">call_end</span>
              </Link>

              {/* Volume / stop AI speech */}
              <button
                onClick={() => {
                  window.speechSynthesis.cancel();
                  setStatus('idle');
                }}
                className="w-16 h-16 rounded-full flex items-center justify-center border border-outline-variant hover:bg-surface-container-high transition-all duration-300 group"
              >
                <span className="material-symbols-outlined text-on-surface-variant group-active:scale-90">
                  {status === 'speaking' ? 'volume_off' : 'volume_up'}
                </span>
              </button>
            </div>
          </div>
        </section>

        {/* ── Live Transcription Panel ─────────────────────────────────────── */}
        <aside className="w-full md:w-[400px] flex flex-col bg-surface-container-low rounded-xl border border-outline-variant h-[calc(100vh-200px)] sticky top-24">

          <div className="p-md border-b border-outline-variant flex justify-between items-center bg-surface-container">
            <h2 className="font-label-caps text-label-caps text-primary uppercase">Live Transcription</h2>
            <span className={`w-2 h-2 rounded-full ${status === 'ended' ? 'bg-error' : 'bg-secondary animate-pulse'}`} />
          </div>

          <div ref={chatRef} className="flex-grow overflow-y-auto p-md space-y-md scroll-smooth">
            {messages.length === 0 && (
              <p className="font-body-md text-on-surface-variant text-center mt-lg italic">
                Connecting to Aura AI...
              </p>
            )}
            {messages.map((msg, i) =>
              msg.role === 'ai' ? (
                <div key={i} className="flex flex-col items-start gap-xs max-w-[85%]">
                  <div className="bg-primary-container text-on-primary-container p-sm rounded-xl rounded-tl-none font-body-md shadow-sm">
                    {msg.text}
                  </div>
                  <span className="font-caption text-caption text-on-surface-variant ml-xs">
                    Aura AI • {msg.time}
                  </span>
                </div>
              ) : (
                <div key={i} className="flex flex-col items-end gap-xs ml-auto max-w-[85%]">
                  <div className="bg-surface-container-highest text-on-surface p-sm rounded-xl rounded-tr-none font-body-md shadow-sm border border-outline-variant">
                    {msg.text}
                  </div>
                  <span className="font-caption text-caption text-on-surface-variant mr-xs">
                    You • {msg.time}
                  </span>
                </div>
              )
            )}

            {status === 'processing' && (
              <div className="flex flex-col items-start gap-xs max-w-[85%] animate-pulse">
                <div className="bg-primary-container/30 text-primary p-sm rounded-xl rounded-tl-none font-body-md italic text-sm">
                  Aura is thinking...
                </div>
              </div>
            )}
          </div>

          <div className="p-md bg-surface-container-high border-t border-outline-variant">
            <div className="flex items-center gap-sm px-sm py-xs bg-surface-container-lowest rounded-full border border-outline-variant">
              <span className="material-symbols-outlined text-outline text-sm">info</span>
              <p className="font-caption text-caption text-on-surface-variant">Secure HIPAA-compliant session</p>
            </div>
          </div>
        </aside>
      </main>

      {/* Footer */}
      <footer className="w-full py-md px-margin-mobile md:px-margin-desktop flex flex-col md:flex-row justify-between items-center gap-sm bg-surface-container border-t border-outline-variant">
        <div className="font-label-caps text-label-caps text-on-surface-variant">VocalHealth AI</div>
        <p className="font-caption text-caption text-secondary">© 2024 VocalHealth AI. HIPAA Compliant &amp; Secure.</p>
        <div className="flex gap-md">
          <a className="font-caption text-caption text-on-surface-variant hover:text-primary underline transition-all duration-300" href="#">Privacy Policy</a>
          <a className="font-caption text-caption text-on-surface-variant hover:text-primary underline transition-all duration-300" href="#">Support</a>
        </div>
      </footer>
    </>
  );
}
