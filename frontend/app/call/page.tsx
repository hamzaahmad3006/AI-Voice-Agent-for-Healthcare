'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';

const BAR_COUNT = 40;

interface ChatMessage {
  role: 'ai' | 'user';
  text: string;
  time: string;
}

const DEMO_MESSAGES: ChatMessage[] = [
  {
    role: 'ai',
    text: "Hello! I'm Aura. I've accessed your recent bloodwork results. Would you like to schedule a follow-up with Dr. Aris today?",
    time: '00:05',
  },
  {
    role: 'user',
    text: 'Yes, please. Does he have any openings around 3 PM?',
    time: '00:15',
  },
  {
    role: 'ai',
    text: 'He has a slot at 3:15 PM. I can book that for you now. Should I confirm?',
    time: '00:28',
  },
  {
    role: 'user',
    text: 'That works perfectly for me.',
    time: '00:35',
  },
];

export default function CallPage(): JSX.Element {
  const [muted, setMuted] = useState(false);
  const [seconds, setSeconds] = useState(42);
  const waveformRef = useRef<HTMLDivElement>(null);
  const barsRef = useRef<HTMLDivElement[]>([]);
  const rafRef = useRef<number | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const chatRef = useRef<HTMLDivElement>(null);

  // ── Timer ────────────────────────────────────────────────────────────────
  useEffect(() => {
    const id = setInterval(() => setSeconds((s) => s + 1), 1000);
    return (): void => clearInterval(id);
  }, []);

  // ── Waveform ─────────────────────────────────────────────────────────────
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
        if (h > 60) {
          bar.classList.replace('bg-primary', 'bg-secondary');
        } else {
          bar.classList.replace('bg-secondary', 'bg-primary');
        }
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

  // ── Auto-scroll chat ──────────────────────────────────────────────────────
  useEffect(() => {
    const el = chatRef.current;
    if (el !== null) el.scrollTop = el.scrollHeight;
  }, []);

  const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
  const secs = (seconds % 60).toString().padStart(2, '0');

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

          {/* Ambient glow */}
          <div className="absolute inset-0 pointer-events-none opacity-20 overflow-hidden">
            <div className="absolute -top-1/4 -left-1/4 w-1/2 h-1/2 bg-primary rounded-full blur-[120px] animate-pulse-glow" />
            <div className="absolute -bottom-1/4 -right-1/4 w-1/2 h-1/2 bg-secondary rounded-full blur-[120px] animate-pulse-glow" style={{ animationDelay: '1s' }} />
          </div>

          {/* AI Avatar */}
          <div className="flex flex-col items-center gap-sm mb-xl z-10">
            <div className="w-24 h-24 rounded-full bg-primary-fixed-dim flex items-center justify-center shadow-lg border-4 border-surface-container-highest">
              <span className="material-symbols-outlined text-primary text-[48px] fill-icon">neurology</span>
            </div>
            <h1 className="font-headline-md text-headline-md text-primary">Aura AI</h1>
            <p className={`font-label-caps text-label-caps tracking-widest uppercase transition-colors ${muted ? 'text-error' : 'text-on-surface-variant'}`}>
              {muted ? 'Microphone Muted' : 'Listening...'}
            </p>
          </div>

          {/* Waveform */}
          <div
            ref={waveformRef}
            className="flex items-center justify-center gap-1 h-32 mb-xl z-10 w-full max-w-lg"
          />

          {/* Controls */}
          <div className="flex flex-col items-center gap-md z-10 w-full max-w-md">
            <div className="font-label-caps text-label-caps text-primary tracking-widest mb-base">
              {mins}:{secs}
            </div>

            <div className="flex items-center gap-lg">
              {/* Mute */}
              <button
                onClick={() => setMuted((m) => !m)}
                className="w-16 h-16 rounded-full flex items-center justify-center border border-outline-variant hover:bg-surface-container-high transition-all duration-300 group"
              >
                <span className={`material-symbols-outlined group-active:scale-90 transition-colors ${muted ? 'text-error' : 'text-on-surface-variant'}`}>
                  {muted ? 'mic_off' : 'mic'}
                </span>
              </button>

              {/* End call → confirmation screen */}
              <Link
                href="/confirmation"
                className="w-20 h-20 rounded-full bg-error text-on-error flex items-center justify-center shadow-lg shadow-error/20 hover:scale-105 active:scale-95 transition-all duration-300"
              >
                <span className="material-symbols-outlined text-[32px] fill-icon">call_end</span>
              </Link>

              {/* Volume */}
              <button className="w-16 h-16 rounded-full flex items-center justify-center border border-outline-variant hover:bg-surface-container-high transition-all duration-300 group">
                <span className="material-symbols-outlined text-on-surface-variant group-active:scale-90">volume_up</span>
              </button>
            </div>
          </div>
        </section>

        {/* ── Live Transcription Panel ─────────────────────────────────────── */}
        <aside className="w-full md:w-[400px] flex flex-col bg-surface-container-low rounded-xl border border-outline-variant h-[calc(100vh-200px)] sticky top-24">

          {/* Panel header */}
          <div className="p-md border-b border-outline-variant flex justify-between items-center bg-surface-container">
            <h2 className="font-label-caps text-label-caps text-primary uppercase">Live Transcription</h2>
            <span className="w-2 h-2 rounded-full bg-secondary animate-pulse" />
          </div>

          {/* Messages */}
          <div ref={chatRef} className="flex-grow overflow-y-auto p-md space-y-md scroll-smooth">
            {DEMO_MESSAGES.map((msg, i) =>
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

            {/* Typing indicator */}
            <div className="flex flex-col items-start gap-xs max-w-[85%] animate-pulse">
              <div className="bg-primary-container/30 text-primary p-sm rounded-xl rounded-tl-none font-body-md italic text-sm">
                Aura is checking calendar...
              </div>
            </div>
          </div>

          {/* HIPAA badge */}
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
