import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'VocalHealth AI | Voice-Powered Healthcare',
  description: 'Book appointments instantly using just your voice.',
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>): JSX.Element {
  return (
    <html className="scroll-smooth" lang="en">
      <body className="bg-mesh text-on-surface font-body-md min-h-screen flex flex-col overflow-x-hidden antialiased">
        {children}
      </body>
    </html>
  );
}
