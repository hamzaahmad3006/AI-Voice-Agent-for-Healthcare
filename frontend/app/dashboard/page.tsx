import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Dashboard — AI Voice Scheduler',
};

export default function DashboardPage(): JSX.Element {
  return (
    <main className="min-h-screen p-6">
      <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
      <p className="mt-2 text-sm text-gray-500">
        Active calls and booking metrics will appear here (Phase 6).
      </p>
    </main>
  );
}
