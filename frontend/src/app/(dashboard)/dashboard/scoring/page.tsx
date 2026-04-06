'use client'

import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { RefreshCw } from 'lucide-react'
import { useScoring } from '@/hooks/use-scoring'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const FEATURE_GROUPS = [
  { label: 'Role signals', keys: ['seniority_score', 'title_relevance', 'is_decision_maker'] },
  { label: 'Publication signals', keys: ['has_recent_pub', 'pub_count_norm', 'h_index_norm'] },
  { label: 'Funding signals', keys: ['has_nih_active', 'nih_award_norm', 'has_private_funding'] },
  { label: 'Contact signals', keys: ['has_email', 'email_confidence', 'has_linkedin_verified'] },
  { label: 'Activity signals', keys: ['is_conference_speaker', 'institution_type_score', 'recency_score'] },
]

export default function ScoringPage() {
  const { config, stats, isLoading, updateConfig, rescoreAll, isRescoring } = useScoring()
  const [weights, setWeights] = useState<Record<string, number>>({})
  const [edited, setEdited] = useState(false)

  const effectiveWeights = { ...(config?.effective_weights || {}), ...weights }

  const handleWeightChange = (key: string, val: string) => {
    const n = parseFloat(val)
    if (!isNaN(n) && n >= 0) {
      setWeights((w) => ({ ...w, [key]: n }))
      setEdited(true)
    }
  }

  const tierData = stats
    ? [
        { tier: 'HIGH', count: stats.tier_distribution?.HIGH || 0, fill: '#16a34a' },
        { tier: 'MEDIUM', count: stats.tier_distribution?.MEDIUM || 0, fill: '#d97706' },
        { tier: 'LOW', count: stats.tier_distribution?.LOW || 0, fill: '#9ca3af' },
      ]
    : []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Lead Scoring</h1>
          <p className="text-muted-foreground">Weighted feature scoring engine (v1)</p>
        </div>
        <Button onClick={rescoreAll} disabled={isRescoring}>
          <RefreshCw className={`mr-2 h-4 w-4 ${isRescoring ? 'animate-spin' : ''}`} />
          {isRescoring ? 'Rescoring…' : 'Rescore All Leads'}
        </Button>
      </div>

      {stats && (
        <div className="grid gap-4 md:grid-cols-4">
          {[
            { label: 'Total Leads', value: stats.total_leads },
            { label: 'Avg Score', value: stats.average_score?.toFixed(1) },
            { label: 'Highest', value: stats.max_score },
            { label: 'Lowest', value: stats.min_score },
          ].map((m) => (
            <Card key={m.label}>
              <CardHeader className="pb-1">
                <CardTitle className="text-sm font-medium text-muted-foreground">{m.label}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{m.value}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Score Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-48" />
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={tierData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="tier" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {tierData.map((entry) => (
                      <Cell key={entry.tier} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Feature Weights</CardTitle>
            {edited && (
              <Button
                size="sm"
                onClick={() => {
                  updateConfig(weights)
                  setEdited(false)
                }}
              >
                Save Weights
              </Button>
            )}
          </CardHeader>
          <CardContent className="max-h-72 space-y-4 overflow-y-auto">
            {FEATURE_GROUPS.map((group) => (
              <div key={group.label}>
                <p className="mb-2 text-xs font-semibold uppercase text-muted-foreground">{group.label}</p>
                <div className="space-y-1">
                  {group.keys.map((key) => (
                    <div key={key} className="flex items-center gap-2">
                      <Label className="w-44 text-xs capitalize">{key.replace(/_/g, ' ')}</Label>
                      <Input
                        type="number"
                        step="0.5"
                        min="0"
                        className="h-7 w-20 text-xs"
                        value={effectiveWeights[key] ?? ''}
                        onChange={(e) => handleWeightChange(key, e.target.value)}
                      />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
