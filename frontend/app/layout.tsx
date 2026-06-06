import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';

export const metadata: Metadata = {
  title: 'AI Voice Scheduler',
  description: 'Healthcare appointment scheduling via AI voice agent',
};

function NavItem({ href, label, icon }: { href: string; label: string; icon: string }): JSX.Element {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-slate-700 hover:text-white"
    >
      <span className="text-base leading-none">{icon}</span>
      {label}
    </Link>
  );
}

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>): JSX.Element {
  return (
    <html lang="en">
      <body className="flex min-h-screen bg-gray-50 text-gray-900 antialiased">
        {/* Sidebar */}
        <aside className="flex w-60 flex-shrink-0 flex-col bg-slate-900 px-4 py-6">
          {/* Logo */}
          <div className="mb-8 px-3">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
              AI Voice Agent
            </p>
            <h1 className="mt-1 text-lg font-bold text-white">Scheduler</h1>
          </div>

          {/* Navigation */}
          <nav className="flex flex-col gap-1">
            <NavItem href="/dashboard" label="Dashboard" icon="⬛" />
            <NavItem href="/sessions"  label="Sessions"  icon="📋" />
            <NavItem href="/health"    label="Health"    icon="🔍" />
          </nav>

          {/* Footer */}
          <div className="mt-auto px-3 pt-6">
            <p className="text-xs text-slate-500">MVP · localhost</p>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </body>
    </html>
  );
}
