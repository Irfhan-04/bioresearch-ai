'use client'

import { Skeleton } from '@/components/ui/skeleton'
import { Users, TrendingUp, Activity, Target } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api/client'
import { ScoreDistributionChart } from '@/components/charts/score-distribution-chart'
import { LeadsTimelineChart } from '@/components/charts/leads-timeline-chart'
import { useAuth } from '@/hooks/use-auth'
import { cn } from '@/lib/utils'

interface DashboardStats {
  total_leads: number
  high_priority_leads: number
  leads_this_month: number
  average_score: number
}

const METRICS = [
  {
    key: 'total_leads' as const,
    label: 'Total Leads',
    sub: 'All time',
    icon: Users,
    accent: '#00d68f',
    glow: 'rgba(0,214,143,0.07)',
    border: 'border-[rgba(0,214,143,0.15)]',
  },
  {
    key: 'high_priority_leads' as const,
    label: 'High Priority',
    sub: 'Score ≥ 70',
    icon: Target,
    accent: '#a78bfa',
    glow: 'rgba(167,139,250,0.07)',
    border: 'border-violet-500/15',
  },
  {
    key: 'leads_this_month' as const,
    label: 'This Month',
    sub: 'New leads',
    icon: TrendingUp,
    accent: '#38bdf8',
    glow: 'rgba(56,189,248,0.07)',
    border: 'border-sky-500/15',
  },
  {
    key: 'average_score' as const,
    label: 'Avg Score',
    sub: 'Quality index',
    icon: Activity,
    accent: '#fbbf24',
    glow: 'rgba(251,191,36,0.07)',
    border: 'border-amber-500/15',
  },
]

export default function DashboardPage() {
  const { user } = useAuth()
  const { data: stats, isLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard', 'stats'],
    queryFn: async () => (await apiClient.get('/dashboard/stats')).data,
  })

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'

  const fmt = (k: keyof DashboardStats) => {
    const v = stats?.[k]
    if (v === undefined) return '—'
    return k === 'average_score' ? (v as number).toFixed(1) : v.toLocaleString()
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="animate-fade-up">
        <p className="text-xs font-mono-dm tracking-widest uppercase text-zinc-600 mb-1">
          {greeting},&nbsp;
          <span className="text-[#00d68f]">{user?.full_name?.split(' ')[0] ?? 'researcher'}</span>
        </p>
        <h1 className="font-syne text-3xl font-700 text-white tracking-tight">Intelligence Overview</h1>
        <p className="text-sm text-zinc-500 mt-1">Your biotech prospecting dashboard — live data, precision scoring.</p>
      </div>

      {/* Metric cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {METRICS.map((m, i) => (
          <div
            key={m.key}
            className={cn('relative rounded-xl overflow-hidden border p-5 animate-fade-up stat-line', m.border)}
            style={{
              animationDelay: `${i * 75}ms`,
              background: `radial-gradient(ellipse at top left, ${m.glow}, transparent 65%), rgba(11,18,36,0.88)`,
              backdropFilter: 'blur(20px)',
              boxShadow: '0 4px 24px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.04)',
            }}
          >
            <div className="flex items-start justify-between mb-4">
              <p className="text-[11px] font-medium uppercase tracking-widest text-zinc-500">{m.label}</p>
              <m.icon className="h-4 w-4 shrink-0" style={{ color: m.accent }} />
            </div>
            {isLoading ? (
              <Skeleton className="h-9 w-20 bg-white/5" />
            ) : (
              <p className="font-mono-dm text-3xl font-500 tracking-tight" style={{ color: m.accent }}>
                {fmt(m.key)}
              </p>
            )}
            <p className="text-xs text-zinc-600 mt-1">{m.sub}</p>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid gap-6 lg:grid-cols-2 animate-fade-up delay-400">
        {[
          { label: 'Score Distribution', dot: '#00d68f', Chart: ScoreDistributionChart },
          { label: 'Leads Timeline',     dot: '#a78bfa', Chart: LeadsTimelineChart },
        ].map(({ label, dot, Chart }) => (
          <div
            key={label}
            className="rounded-xl border border-[rgba(255,255,255,0.06)] p-5"
            style={{
              background: 'rgba(11,18,36,0.85)',
              backdropFilter: 'blur(20px)',
              boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
            }}
          >
            <p className="font-syne text-sm font-600 text-zinc-200 mb-4 flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full inline-block" style={{ background: dot }} />
              {label}
            </p>
            <Chart />
          </div>
        ))}
      </div>
    </div>
  )
}