'use client'

import { useQuery } from '@tanstack/react-query'
import { Database, Server, Wifi } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { apiClient } from '@/lib/api/client'

interface SystemHealth {
  database: 'ok' | 'error'
  redis: 'ok' | 'error'
  api: 'ok' | 'error'
  checked_at: string
}

interface RevenueStats {
  mrr: number
  arr: number
  subscribers: { pro: number; team: number; enterprise: number; total: number }
}

interface PlatformStats {
  total_users: number
  active_users_30d: number
  total_leads: number
  total_searches: number
  total_exports: number
}

function StatusBadge({ status }: { status: 'ok' | 'error' }) {
  return (
    <Badge className={status === 'ok' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
      {status}
    </Badge>
  )
}

export default function AdminPage() {
  const { data: health, isLoading: healthLoading } = useQuery<SystemHealth>({
    queryKey: ['admin', 'health'],
    queryFn: () => apiClient.get('/admin/health/system').then((r) => r.data),
    refetchInterval: 30_000,
  })

  const { data: revenue, isLoading: revLoading } = useQuery<RevenueStats>({
    queryKey: ['analytics', 'revenue'],
    queryFn: () => apiClient.get('/analytics/revenue/summary').then((r) => r.data),
  })

  const { data: platform, isLoading: platformLoading } = useQuery<PlatformStats>({
    queryKey: ['analytics', 'admin'],
    queryFn: () => apiClient.get('/analytics/admin/overview').then((r) => r.data),
  })

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Admin overview</h1>
        <p className="mt-1 text-muted-foreground">System health and platform metrics.</p>
      </div>

      <section>
        <h2 className="text-sm font-medium text-muted-foreground mb-3 uppercase tracking-wider">
          System health
        </h2>
        {healthLoading ? (
          <div className="grid gap-4 md:grid-cols-3">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            {[
              { label: 'Database', status: health?.database, icon: Database },
              { label: 'Redis cache', status: health?.redis, icon: Wifi },
              { label: 'API', status: health?.api, icon: Server },
            ].map(({ label, status, icon: Icon }) => (
              <Card key={label}>
                <CardHeader className="pb-2 flex-row items-center justify-between">
                  <CardTitle className="text-sm font-medium">{label}</CardTitle>
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <StatusBadge status={(status as 'ok' | 'error') ?? 'error'} />
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-sm font-medium text-muted-foreground mb-3 uppercase tracking-wider">
          Revenue
        </h2>
        {revLoading ? (
          <div className="grid gap-4 md:grid-cols-4">
            {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24" />)}
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">MRR</CardTitle></CardHeader>
              <CardContent><p className="text-2xl font-semibold">${(revenue?.mrr ?? 0).toLocaleString()}</p></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">ARR</CardTitle></CardHeader>
              <CardContent><p className="text-2xl font-semibold">${(revenue?.arr ?? 0).toLocaleString()}</p></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Pro subscribers</CardTitle></CardHeader>
              <CardContent><p className="text-2xl font-semibold">{revenue?.subscribers.pro ?? 0}</p></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Team subscribers</CardTitle></CardHeader>
              <CardContent><p className="text-2xl font-semibold">{revenue?.subscribers.team ?? 0}</p></CardContent>
            </Card>
          </div>
        )}
      </section>

      <section>
        <h2 className="text-sm font-medium text-muted-foreground mb-3 uppercase tracking-wider">
          Platform activity
        </h2>
        {platformLoading ? (
          <div className="grid gap-4 md:grid-cols-3">
            {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-24" />)}
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            {[
              { label: 'Total users', value: platform?.total_users ?? 0 },
              { label: 'Active users (30d)', value: platform?.active_users_30d ?? 0 },
              { label: 'Total leads', value: platform?.total_leads ?? 0 },
            ].map(({ label, value }) => (
              <Card key={label}>
                <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle></CardHeader>
                <CardContent><p className="text-2xl font-semibold">{value.toLocaleString()}</p></CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
