import type { Metadata } from 'next'
import './globals.css'
import { QueryProvider } from '@/providers/query-provider'
import { Toaster } from '@/components/ui/toaster'

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL ?? 'http://localhost:3000'),
  title: {
    default: 'BioResearch AI',
    template: '%s — BioResearch AI',
  },
  description:
    'AI-powered biotech research intelligence. Discover and rank researchers by relevance using XGBoost, sentence-transformers, and SHAP explanations.',
  keywords: [
    'biotech research intelligence',
    'researcher discovery',
    'drug discovery AI',
    'DILI research',
    'organoid research',
    'semantic search biotech',
  ],
  authors: [{ name: 'BioResearch AI' }],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased">
        <QueryProvider>{children}</QueryProvider>
        <Toaster />
      </body>
    </html>
  )
}
