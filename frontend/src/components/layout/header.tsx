'use client'

import { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import { Bell } from 'lucide-react'
import { cn } from '@/lib/utils'

const PAGE_LABELS: Record<string, string> = {
  dashboard:     'Overview',
  leads:         'Leads',
  search:        'Search',
  pipelines:     'Pipelines',
  analytics:     'Analytics',
  reports:       'Reports',
  alerts:        'Smart Alerts',
  crm:           'CRM',
  collaboration: 'Collaboration',
  scoring:       'Lead Scoring',
  exports:       'Exports',
  teams:         'Teams',
  settings:      'Settings',
  billing:       'Billing',
  'api-keys':    'API Keys',
  danger:        'Danger Zone',
}

export function Header({ title }: { title?: string }) {
  const pathname = usePathname()
  const [time, setTime] = useState('')
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    const tick = () =>
      setTime(
        new Date().toLocaleTimeString('en-US', {
          hour: '2-digit', minute: '2-digit', second: '2-digit',
          hour12: false,
        })
      )
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  // Build breadcrumb from pathname
  const segments = pathname.split('/').filter(Boolean)
  const crumbs = segments.map((seg, i) => ({
    label: PAGE_LABELS[seg] ?? seg.charAt(0).toUpperCase() + seg.slice(1),
    isLast: i === segments.length - 1,
  }))

  const pageTitle = title
    ? (PAGE_LABELS[title.toLowerCase()] ?? title)
    : crumbs[crumbs.length - 1]?.label ?? 'Dashboard'

  return (
    <header className="flex h-14 items-center justify-between border-b border-[rgba(255,255,255,0.055)] px-6 glass shrink-0">
      {/* Left: breadcrumb */}
      <div className="flex items-center gap-2">
        <nav className="flex items-center gap-1.5 text-xs text-zinc-600">
          {crumbs.map((c, i) => (
            <span key={i} className="flex items-center gap-1.5">
              {i > 0 && <span className="text-zinc-700">/</span>}
              <span className={cn(
                c.isLast ? 'font-syne font-600 text-zinc-100 text-sm' : 'text-zinc-500'
              )}>
                {c.label}
              </span>
            </span>
          ))}
        </nav>
      </div>

      {/* Right: live clock + bell */}
      <div className="flex items-center gap-4">
        {mounted && (
          <span className="font-mono-dm text-xs text-zinc-600 tabular-nums tracking-wider hidden sm:block">
            {time}
          </span>
        )}
        <div className="h-4 w-px bg-zinc-800 hidden sm:block" />
        <button className="relative flex h-8 w-8 items-center justify-center rounded-md hover:bg-white/[0.05] transition-colors group">
          <Bell className="h-4 w-4 text-zinc-500 group-hover:text-zinc-300 transition-colors" />
          {/* Notification dot */}
          <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-[#00d68f] animate-pulse-glow" />
        </button>
      </div>
    </header>
  )
}