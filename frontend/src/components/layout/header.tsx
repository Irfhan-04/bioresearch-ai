'use client'

import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'

const PAGE_LABELS: Record<string, string> = {
  dashboard: 'Overview',
  researchers: 'Researchers',
  search: 'Search',
  scoring: 'Scoring',
  settings: 'Settings',
  'api-keys': 'API Keys',
  danger: 'Danger Zone',
}

export function Header({ title }: { title?: string }) {
  const pathname = usePathname()
  const segments = pathname.split('/').filter(Boolean)
  const crumbs = segments.map((seg, i) => ({
    label: PAGE_LABELS[seg] ?? seg.charAt(0).toUpperCase() + seg.slice(1),
    isLast: i === segments.length - 1,
  }))

  const pageTitle = title ? (PAGE_LABELS[title.toLowerCase()] ?? title) : crumbs[crumbs.length - 1]?.label ?? 'Dashboard'

  return (
    <header className="flex h-14 items-center justify-between border-b border-[rgba(255,255,255,0.055)] px-6 glass shrink-0">
      <div className="flex items-center gap-3">
        <p className="text-xs uppercase tracking-widest text-zinc-500">BioResearch AI</p>
        <div className="h-4 w-px bg-zinc-800" />
        <p className="font-syne text-sm text-zinc-200">{pageTitle}</p>
      </div>

      <nav className="flex items-center gap-1.5 text-xs text-zinc-600">
        {crumbs.map((c, i) => (
          <span key={i} className="flex items-center gap-1.5">
            {i > 0 && <span className="text-zinc-700">/</span>}
            <span className={cn(c.isLast ? 'font-syne font-600 text-zinc-100 text-sm' : 'text-zinc-500')}>{c.label}</span>
          </span>
        ))}
      </nav>
    </header>
  )
}
