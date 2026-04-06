'use client'

import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { useAnalytics } from '@/hooks/use-analytics'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const COLORS = ['#667eea', '#16a34a', '#d97706', '#dc2626', '#8b5cf6', '#0ea5e9']

export default function AnalyticsPage() {
  const [days] = useState(30)
  const { daily, topSources, engagement, isLoading } = useAnalytics(days)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Analytics</h1>
        <p className="text-muted-foreground">Your activity and lead generation metrics</p>
      </div>

      {engagement && (
        <div className="grid gap-4 md:grid-cols-3">
          {[
            { title: 'Weekly Active', value: engagement.weekly_active_days, suffix: 'days' },
            { title: 'Current Streak', value: engagement.current_streak, suffix: 'days' },
            { title: 'Longest Streak', value: engagement.longest_streak, suffix: 'days' },
          ].map((m) => (
            <Card key={m.title}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">{m.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {m.value} <span className="text-sm font-normal text-muted-foreground">{m.suffix}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Tabs defaultValue="daily">
        <TabsList>
          <TabsTrigger value="daily">Daily Activity</TabsTrigger>
          <TabsTrigger value="sources">Top Sources</TabsTrigger>
        </TabsList>

        <TabsContent value="daily" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Leads Created — Last {days} Days</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-64 w-full" />
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={daily?.data || []}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" fill="#667eea" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sources" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Leads by Data Source</CardTitle>
            </CardHeader>
            <CardContent className="flex items-center gap-8">
              {isLoading ? (
                <Skeleton className="h-64 w-full" />
              ) : (
                <>
                  <ResponsiveContainer width="50%" height={240}>
                    <PieChart>
                      <Pie
                        data={topSources?.sources || []}
                        dataKey="count"
                        nameKey="source"
                        cx="50%"
                        cy="50%"
                        outerRadius={90}
                        label={({ source, percent }) => `${source} ${(percent * 100).toFixed(0)}%`}
                      >
                        {(topSources?.sources || []).map((_: any, i: number) => (
                          <Cell key={i} fill={COLORS[i % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="space-y-2">
                    {(topSources?.sources || []).map((s: any, i: number) => (
                      <div key={s.source} className="flex items-center gap-2 text-sm">
                        <span className="inline-block h-3 w-3 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                        <span className="capitalize">{s.source}</span>
                        <span className="text-muted-foreground">{s.count} leads</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
