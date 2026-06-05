import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Sessions — AI Voice Scheduler',
};

export default function SessionsPage(): JSX.Element {
  return (
    <main className="min-h-screen p-6">
      <h1 className="text-2xl font-semibold text-gray-900">Sessions</h1>
      <p className="mt-2 text-sm text-gray-500">
        Session list and detail views will appear here (Phase 6).
      </p>
    </main>
  );
}
