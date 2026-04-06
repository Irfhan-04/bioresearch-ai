'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api/client'

interface UsageSummary {
  tier: string
  leads_created: number
  leads_limit: number
  leads_remaining: number
  quota_pct_used: number
  searches_run: number
  exports_made: number
}

export function UsageMeter() {
  const { data, isLoading } = useQuery<UsageSummary>({
    queryKey: ['usage', 'summary'],
    queryFn: () => apiClient.get('/users/me/usage').then((response) => response.data),
    refetchInterval: 60_000,
  })

  if (isLoading || !data) {
    return <div className="glass-card h-24 animate-pulse rounded-xl" />
  }

  const pct = Math.min(data.quota_pct_used, 100)
  const barColor = pct > 90 ? '#fb7185' : pct > 70 ? '#fbbf24' : '#00d68f'
  const tierTone =
    data.tier === 'pro'
      ? 'border-[rgba(0,214,143,0.35)] text-[#00d68f]'
      : data.tier === 'team'
        ? 'border-violet-500/35 text-violet-300'
        : data.tier === 'enterprise'
          ? 'border-amber-500/35 text-amber-300'
          : 'border-zinc-700 text-zinc-400'

  return (
    <div className="glass-card rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-widest text-zinc-500">Monthly Leads</p>
          <p className="mt-1 text-2xl font-semibold text-zinc-100">
            {data.leads_created.toLocaleString()}
            <span className="ml-1 text-sm font-normal text-zinc-500">/ {data.leads_limit.toLocaleString()}</span>
          </p>
        </div>
        <span className={`font-mono-dm rounded border px-2 py-1 text-[10px] uppercase tracking-widest ${tierTone}`}>
          {data.tier.toUpperCase()}
        </span>
      </div>

      <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
        <div
          className="h-2 rounded-full transition-all duration-500"
          style={{
            width: `${pct}%`,
            background: barColor,
            boxShadow: `0 0 18px ${barColor}55`,
          }}
        />
      </div>
      <p className="mt-2 text-xs text-zinc-500">{data.leads_remaining.toLocaleString()} remaining this month</p>

      {pct >= 80 && (
        <Link href="/settings/billing" className="mt-3 block text-center text-xs font-medium text-[#00d68f] hover:underline">
          {pct >= 100 ? 'Quota exceeded - upgrade now' : 'Upgrade for more leads ->'}
        </Link>
      )}
    </div>
  )
}
