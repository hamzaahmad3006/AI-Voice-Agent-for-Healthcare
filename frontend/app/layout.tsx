import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AI Voice Scheduler',
  description: 'Healthcare appointment scheduling via AI voice agent',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): JSX.Element {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        {children}
      </body>
    </html>
  );
}
