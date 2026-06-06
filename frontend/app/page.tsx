'use client';

import Link from 'next/link';
import { useState } from 'react';

export default function LandingPage(): JSX.Element {
  const [listening, setListening] = useState(false);

  const toggle = (): void => setListening((v) => !v);

  return (
    <>
      {/* Top Navigation Bar */}
      <header className="fixed top-0 left-0 w-full z-50 flex justify-between items-center px-margin-mobile md:px-margin-desktop h-16 bg-surface/70 backdrop-blur-xl shadow-sm">
        <div className="font-headline-md text-headline-md font-bold text-primary">
          VocalHealth AI
        </div>
        <nav className="hidden md:flex gap-lg items-center">
          <a className="font-label-caps text-label-caps text-primary border-b-2 border-primary transition-colors duration-300" href="#">
            HOME
          </a>
          <Link className="font-label-caps text-label-caps text-on-surface-variant hover:text-primary transition-colors duration-300" href="/dashboard">
            DASHBOARD
          </Link>
          <a className="font-label-caps text-label-caps text-on-surface-variant hover:text-primary transition-colors duration-300" href="#">
            SECURITY
          </a>
        </nav>
        <div className="flex items-center gap-sm">
          <button className="p-xs text-on-surface-variant hover:text-primary transition-all duration-300 active:scale-95">
            <span className="material-symbols-outlined">account_circle</span>
          </button>
          <button className="p-xs text-on-surface-variant hover:text-primary transition-all duration-300 active:scale-95">
            <span className="material-symbols-outlined">settings</span>
          </button>
        </div>
      </header>

      {/* Hero */}
      <main className="flex-grow flex items-center justify-center px-margin-mobile pt-32 pb-24">
        <div className="max-w-4xl w-full flex flex-col items-center text-center">

          {/* Voice wave visualizer */}
          <div className="mb-xl relative">
            <div className="absolute inset-0 bg-primary/10 blur-3xl rounded-full" />
            <div className="relative flex items-center justify-center gap-1 h-12">
              {[
                { delay: '0.1s', h: 'h-6' },
                { delay: '0.2s', h: 'h-10' },
                { delay: '0.3s', h: 'h-8' },
                { delay: '0.4s', h: 'h-12' },
                { delay: '0.5s', h: 'h-6' },
              ].map((bar, i) => (
                <div
                  key={i}
                  className={`w-1.5 ${bar.h} rounded-full voice-wave ${i % 2 === 0 ? 'bg-primary' : 'bg-secondary'}`}
                  style={{
                    animationDelay: bar.delay,
                    animationDuration: listening ? '0.4s' : '2s',
                  }}
                />
              ))}
            </div>
          </div>

          {/* Glassmorphism card */}
          <section className="glass-card p-lg md:p-xl rounded-xl shadow-[0_20px_50px_rgba(0,62,199,0.1)] w-full max-w-2xl transform transition-all duration-500 hover:shadow-[0_25px_60px_rgba(0,62,199,0.15)]">
            <div className="mb-md">
              <span className="font-label-caps text-label-caps bg-secondary-container text-on-secondary-container px-sm py-xs rounded-full inline-block mb-sm">
                AI POWERED CARE
              </span>
              <h1 className="font-headline-lg-mobile md:font-headline-lg text-headline-lg-mobile md:text-headline-lg text-on-surface mb-md">
                Your Personal Voice Healthcare Assistant
              </h1>
              <p className="font-body-lg text-body-lg text-on-surface-variant max-w-lg mx-auto mb-lg">
                Book appointments instantly using just your voice. Our AI assistant handles the details while you stay focused on your health.
              </p>
            </div>

            <div className="flex flex-col items-center gap-md">
              <button
                onClick={toggle}
                className={`group relative px-lg py-md rounded-full font-headline-md text-headline-md flex items-center gap-sm shadow-lg hover:shadow-xl transition-all duration-300 active:scale-95 ${
                  listening
                    ? 'bg-secondary text-on-secondary'
                    : 'bg-primary text-on-primary hover:bg-primary-container'
                }`}
              >
                <span className={`material-symbols-outlined text-[32px] ${listening ? 'animate-pulse' : ''}`}>
                  mic
                </span>
                <span>{listening ? 'Listening…' : 'Start Voice Appointment'}</span>
                <div className="absolute -inset-1 bg-primary/20 rounded-full blur opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              </button>

              <p className="font-caption text-caption text-outline flex items-center gap-xs">
                <span className="material-symbols-outlined text-[16px]">verified_user</span>
                HIPAA Compliant. Encrypted Voice Streaming.
              </p>
            </div>
          </section>

          {/* Feature pills */}
          <div className="mt-xl grid grid-cols-1 md:grid-cols-3 gap-md w-full max-w-4xl">
            {[
              { icon: 'schedule',       label: 'INSTANT BOOKING'    },
              { icon: 'clinical_notes', label: 'SECURE RECORDS'     },
              { icon: 'language',       label: '24/7 ACCESSIBILITY' },
            ].map(({ icon, label }) => (
              <div key={label} className="glass-card p-md rounded-lg flex flex-col items-center gap-xs">
                <span className="material-symbols-outlined text-primary">{icon}</span>
                <p className="font-label-caps text-label-caps">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Background decoration */}
      <div className="fixed bottom-0 right-0 -z-10 w-1/3 opacity-20 pointer-events-none hidden lg:block">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          alt="Healthcare background"
          className="w-full h-full object-cover grayscale brightness-110"
          src="https://lh3.googleusercontent.com/aida-public/AB6AXuCEClG1ZKinDFn0HKSfUBZyM9C1rRQBZDpCcFDnFq6v8bf0qARXT4JV0ynnn9heysIcNSL8X43I-8W4x4AdXYDLlGaloG1ix96r0cZtWftoUy_eFrIVQuG3U6JEIUImibt-8YFwrHHA9M8xUvTG_4wSZSwbiz4ibepRx_baD5rofxmkXOXwMCAnjNUyQiERHtjUAVBR6PUD7CSIVFEQ3L8QlOCVdy_Iswdm0ichYvoMmZRa2NY1W_uVKSn7sGGK-H6O6iO_rsgjLrg9"
        />
      </div>

      {/* Footer */}
      <footer className="w-full py-md px-margin-mobile md:px-margin-desktop flex flex-col md:flex-row justify-between items-center gap-sm bg-surface-container border-t border-outline-variant">
        <div className="flex flex-col md:flex-row items-center gap-md">
          <span className="font-label-caps text-label-caps text-on-surface-variant">VOCALHEALTH AI</span>
          <span className="font-caption text-caption text-secondary">© 2024 VocalHealth AI. HIPAA Compliant &amp; Secure.</span>
        </div>
        <nav className="flex flex-wrap justify-center gap-md">
          {['Privacy Policy', 'Terms of Service', 'Security Compliance', 'Support'].map((item) => (
            <a key={item} className="font-caption text-caption text-on-surface-variant hover:text-primary transition-all duration-300 underline" href="#">
              {item}
            </a>
          ))}
        </nav>
      </footer>
    </>
  );
}
