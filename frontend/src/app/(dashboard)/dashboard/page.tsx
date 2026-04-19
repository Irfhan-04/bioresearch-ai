'use client';
import { Skeleton } from '@/components/ui/skeleton';
import { Users, Target, Microscope, Search } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { ScoreDistributionChart } from '@/components/charts/score-distribution-chart';
import { ResearchersTimelineChart } from '@/components/charts/researchers-timeline-chart';
import { ResearchAreaDonutChart } from '@/components/charts/ResearchAreaDonutChart';
import { useAuth } from '@/hooks/use-auth';
import { cn } from '@/lib/utils';

interface DashboardStats {
  total_researchers: number
  high_relevance: number
  research_areas_covered: number
  queries_today: number
  area_breakdown?: Array<{ area: string; count: number }>
  model_version?: string
  model_trained_at?: string | null
  n_training_samples?: number
  macro_f1?: number
}

const METRICS = [
  { key: 'total_researchers' as const, label: 'Researchers Indexed', sub: 'All indexed profiles', icon: Users, accent: '#00d68f', glow: 'rgba(0,214,143,0.07)', border: 'border-[rgba(0,214,143,0.15)]' },
  { key: 'high_relevance' as const, label: 'High Relevance', sub: 'Tier: High', icon: Target, accent: '#a78bfa', glow: 'rgba(167,139,250,0.07)', border: 'border-violet-500/15' },
  { key: 'research_areas_covered' as const, label: 'Research Areas Covered', sub: 'Distinct domains', icon: Microscope, accent: '#38bdf8', glow: 'rgba(56,189,248,0.07)', border: 'border-sky-500/15' },
  { key: 'queries_today' as const, label: 'Queries Today', sub: 'Semantic queries', icon: Search, accent: '#fbbf24', glow: 'rgba(251,191,36,0.07)', border: 'border-amber-500/15' },
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
    if (v === undefined || v === null) return '—'
    return typeof v === 'number' ? v.toLocaleString() : String(v)
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="animate-fade-up">
        <p className="mb-1 text-xs font-mono-dm uppercase tracking-widest text-zinc-600">
          {greeting}, <span className="text-[#00d68f]">{user?.full_name?.split(' ')[0] ?? 'researcher'}</span>
        </p>
        <h1 className="font-syne text-3xl font-700 tracking-tight text-white">Overview</h1>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {METRICS.map((m, i) => (
          <div
            key={m.key}
            className={cn('stat-line relative overflow-hidden rounded-xl border p-5 animate-fade-up', m.border)}
            style={{
              animationDelay: `${i * 75}ms`,
              background: `radial-gradient(ellipse at top left, ${m.glow}, transparent 65%), rgba(11,18,36,0.88)`,
              backdropFilter: 'blur(20px)',
              boxShadow: '0 4px 24px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.04)',
            }}
          >
            <div className="mb-4 flex items-start justify-between">
              <p className="text-[11px] font-medium uppercase tracking-widest text-zinc-500">{m.label}</p>
              <m.icon className="h-4 w-4 shrink-0" style={{ color: m.accent }} />
            </div>
            {isLoading ? <Skeleton className="h-9 w-20 bg-white/5" /> : <p className="font-mono-dm text-3xl font-500 tracking-tight" style={{ color: m.accent }}>{fmt(m.key)}</p>}
            <p className="mt-1 text-xs text-zinc-600">{m.sub}</p>
          </div>
        ))}
      </div>

      <section className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-border bg-surface p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-text-muted">Researchers by Domain</h2>
          <ResearchAreaDonutChart data={stats?.area_breakdown ?? []} />
        </div>

        <div className="rounded-xl border border-border bg-surface p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-text-muted">Model Status</h2>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between"><dt className="text-text-muted">Algorithm</dt><dd className="font-mono text-text-primary">{stats?.model_version ?? 'RandomForest v1'}</dd></div>
            <div className="flex justify-between"><dt className="text-text-muted">Last Trained</dt><dd className="font-mono text-text-primary">{stats?.model_trained_at ? new Date(stats.model_trained_at).toLocaleDateString() : '—'}</dd></div>
            <div className="flex justify-between"><dt className="text-text-muted">Training Samples</dt><dd className="font-mono text-text-primary">{stats?.n_training_samples ?? 800}</dd></div>
            <div className="flex justify-between"><dt className="text-text-muted">Macro F1</dt><dd className="font-mono text-teal-400">{stats?.macro_f1 ? stats.macro_f1.toFixed(3) : '—'}</dd></div>
          </dl>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2 animate-fade-up delay-400">
        {[{ label: 'Score Distribution', dot: '#00d68f', Chart: ScoreDistributionChart }, { label: 'Researchers Timeline', dot: '#a78bfa', Chart: ResearchersTimelineChart }].map(({ label, dot, Chart }) => (
          <div key={label} className="rounded-xl border border-[rgba(255,255,255,0.06)] p-5" style={{ background: 'rgba(11,18,36,0.85)', backdropFilter: 'blur(20px)', boxShadow: '0 4px 24px rgba(0,0,0,0.4)' }}>
            <p className="mb-4 flex items-center gap-2 font-syne text-sm font-600 text-zinc-200"><span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: dot }} />{label}</p>
            <Chart />
          </div>
        ))}
      </div>
    </div>
  )
}
