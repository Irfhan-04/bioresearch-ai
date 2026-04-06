import type { Metadata } from 'next'
import './globals.css'
import { QueryProvider } from '@/providers/query-provider'
import { Toaster } from '@/components/ui/toaster'

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL ?? 'http://localhost:3000'),
  title: {
    default: 'Biotech Lead Generator - Find & Score Research Prospects',
    template: '%s | Biotech Lead Generator',
  },
  description:
    'AI-powered lead generation for biotech and pharma business development. Find, enrich, and score researchers interested in 3D in-vitro models and drug discovery tools.',
  keywords: [
    'biotech lead generation',
    'pharma business development',
    '3D in-vitro models leads',
    'drug discovery prospects',
    'PubMed lead scoring',
    'toxicology researcher leads',
  ],
  authors: [{ name: 'Biotech Lead Generator' }],
  openGraph: {
    type: 'website',
    locale: 'en_US',
    siteName: 'Biotech Lead Generator',
    title: 'Biotech Lead Generator - Find & Score Research Prospects',
    description:
      'Find biotech and pharma researchers interested in 3D in-vitro models. AI-powered scoring and enrichment from PubMed, NIH, and conference data.',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Biotech Lead Generator',
    description: 'AI-powered lead generation for biotech BD teams.',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true },
  },
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
