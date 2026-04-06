'use client'

import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useReports } from '@/hooks/use-reports'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

export default function ReportsPage() {
  const { funnel, conversion, roi, cohort, isLoading, roiParams, setRoiParams, runCustom, customData, isRunningCustom } =
    useReports()
  const [customForm, setCustomForm] = useState({ metric: 'lead_count', group_by: 'week', days: 30 })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Reports</h1>
        <p className="text-muted-foreground">Pipeline analytics and lead funnel insights</p>
      </div>

      <Tabs defaultValue="funnel">
        <TabsList>
          <TabsTrigger value="funnel">Funnel</TabsTrigger>
          <TabsTrigger value="conversion">Conversion</TabsTrigger>
          <TabsTrigger value="roi">ROI</TabsTrigger>
          <TabsTrigger value="cohort">Cohort</TabsTrigger>
          <TabsTrigger value="custom">Custom</TabsTrigger>
        </TabsList>

        <TabsContent value="funnel" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Lead Status Funnel</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-64" />
              ) : (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={funnel?.stages || []} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis dataKey="stage" type="category" width={110} tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#667eea" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="conversion" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Stage-to-Stage Conversion Rates</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-64" />
              ) : (
                <div className="space-y-3">
                  <div className="text-2xl font-bold text-green-600">
                    {conversion?.overall_win_rate}%{' '}
                    <span className="text-sm font-normal text-muted-foreground">overall win rate</span>
                  </div>
                  {(conversion?.transitions || []).map((t: any) => (
                    <div key={`${t.from}-${t.to}`} className="flex items-center gap-3 text-sm">
                      <span className="w-28 font-medium">
                        {t.from} → {t.to}
                      </span>
                      <div className="h-2 flex-1 rounded-full bg-muted">
                        <div className="h-2 rounded-full bg-primary" style={{ width: `${t.rate_pct}%` }} />
                      </div>
                      <span className="w-12 text-right">{t.rate_pct}%</span>
                      <span className="w-24 text-muted-foreground">
                        {t.from_count} → {t.to_count}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="roi" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Pipeline ROI Estimate</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label>Avg Deal Value ($)</Label>
                  <Input
                    type="number"
                    value={roiParams.avgDealValue}
                    onChange={(e) => setRoiParams((p) => ({ ...p, avgDealValue: Number(e.target.value) }))}
                  />
                </div>
                <div className="space-y-1">
                  <Label>Win Rate (%)</Label>
                  <Input
                    type="number"
                    min="0"
                    max="100"
                    value={roiParams.winRatePct}
                    onChange={(e) => setRoiParams((p) => ({ ...p, winRatePct: Number(e.target.value) }))}
                  />
                </div>
              </div>
              {roi && (
                <div className="rounded-lg border border-green-200 bg-green-50 p-4">
                  <div className="text-3xl font-bold text-green-700">${roi.total_pipeline_value.toLocaleString()}</div>
                  <div className="text-sm text-green-600">Estimated pipeline value</div>
                  <div className="mt-3 space-y-1">
                    {(roi.tier_breakdown || []).map((t: any) => (
                      <div key={t.tier} className="flex justify-between text-sm">
                        <span>
                          {t.tier} tier ({t.lead_count} leads × {t.multiplier}x)
                        </span>
                        <span className="font-medium">${t.expected_value.toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="cohort" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Weekly Cohort Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-64" />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="py-2 pr-4 text-left font-medium">Week</th>
                        <th className="px-3 py-2 text-right font-medium">Total Leads</th>
                        <th className="px-3 py-2 text-right font-medium">Activated</th>
                        <th className="px-3 py-2 text-right font-medium">Rate</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(cohort?.cohorts || []).map((c: any) => (
                        <tr key={c.cohort_week} className="border-b hover:bg-muted/50">
                          <td className="py-2 pr-4">{c.cohort_week}</td>
                          <td className="px-3 py-2 text-right">{c.total_leads}</td>
                          <td className="px-3 py-2 text-right">{c.activated}</td>
                          <td className="px-3 py-2 text-right">
                            <span className={c.activation_rate > 20 ? 'font-medium text-green-600' : ''}>
                              {c.activation_rate}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="custom" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Custom Report Builder</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-1">
                  <Label>Metric</Label>
                  <Select value={customForm.metric} onValueChange={(v) => setCustomForm((f) => ({ ...f, metric: v }))}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {['lead_count', 'avg_score', 'high_value_count', 'contacted_count', 'won_count', 'enriched_count'].map((m) => (
                        <SelectItem key={m} value={m}>
                          {m.replace(/_/g, ' ')}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label>Group by</Label>
                  <Select value={customForm.group_by} onValueChange={(v) => setCustomForm((f) => ({ ...f, group_by: v }))}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="day">Day</SelectItem>
                      <SelectItem value="week">Week</SelectItem>
                      <SelectItem value="month">Month</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label>Days</Label>
                  <Input
                    type="number"
                    value={customForm.days}
                    onChange={(e) => setCustomForm((f) => ({ ...f, days: Number(e.target.value) }))}
                  />
                </div>
              </div>
              <Button onClick={() => runCustom(customForm)} disabled={isRunningCustom}>
                {isRunningCustom ? 'Running...' : 'Run Report'}
              </Button>
              {customData && (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={customData.data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="value" fill="#667eea" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
