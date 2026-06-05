import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Health — AI Voice Scheduler',
};

export default function HealthPage(): JSX.Element {
  return (
    <main className="min-h-screen p-6">
      <h1 className="text-2xl font-semibold text-gray-900">Service Health</h1>
      <p className="mt-2 text-sm text-gray-500">
        Backend service health checks will appear here (Phase 6).
      </p>
    </main>
  );
}
