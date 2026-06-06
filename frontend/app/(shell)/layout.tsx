import Link from 'next/link';

function NavItem({ href, icon, label }: { href: string; icon: string; label: string }): JSX.Element {
  return (
    <Link
      href={href}
      className="flex items-center gap-sm px-sm py-xs rounded-lg font-label-caps text-label-caps text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface transition-all duration-200"
    >
      <span className="material-symbols-outlined text-[20px]">{icon}</span>
      {label}
    </Link>
  );
}

export default function ShellLayout({
  children,
}: Readonly<{ children: React.ReactNode }>): JSX.Element {
  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar */}
      <aside className="flex w-64 flex-shrink-0 flex-col border-r border-outline-variant bg-surface-container-lowest px-md py-lg">
        {/* Brand */}
        <div className="mb-lg px-xs">
          <span className="font-label-caps text-label-caps text-secondary">VOCALHEALTH AI</span>
          <h1 className="mt-xs font-headline-md text-headline-md text-on-surface">Dashboard</h1>
        </div>

        {/* Nav */}
        <nav className="flex flex-col gap-xs">
          <NavItem href="/dashboard" icon="dashboard"      label="OVERVIEW"  />
          <NavItem href="/sessions"  icon="format_list_bulleted" label="SESSIONS"  />
          <NavItem href="/health"    icon="monitor_heart"  label="HEALTH"    />
        </nav>

        {/* Footer */}
        <div className="mt-auto pt-lg">
          <div className="rounded-lg bg-surface-container-low px-sm py-xs">
            <p className="font-label-caps text-label-caps text-on-surface-variant">MVP · localhost:8000</p>
          </div>
        </div>
      </aside>

      {/* Top bar + content */}
      <div className="flex flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-outline-variant bg-surface-container-lowest px-md">
          <span className="font-label-caps text-label-caps text-on-surface-variant">AI VOICE AGENT</span>
          <div className="flex items-center gap-sm">
            <Link href="/" className="font-label-caps text-label-caps text-primary hover:underline">
              ← Back to Home
            </Link>
            <button className="p-xs text-on-surface-variant hover:text-primary transition-colors">
              <span className="material-symbols-outlined text-[20px]">account_circle</span>
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-md">
          {children}
        </main>
      </div>
    </div>
  );
}
