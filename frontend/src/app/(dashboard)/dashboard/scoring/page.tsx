'use client'

import { useEffect, useMemo, useState } from 'react'
import { RefreshCw } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ModelMetricsDashboard } from '@/components/charts/ModelMetricsDashboard'
import { ScoreDistributionChart } from '@/components/charts/score-distribution-chart'
import { researchersService, ModelMetrics } from '@/lib/api/researchers-service'
import { useScoring } from '@/hooks/use-scoring'

export default function ScoringPage() {
  const { stats, rescoreAll, isRescoring } = useScoring()
  const [metrics, setMetrics] = useState<ModelMetrics | null>(null)
  const [loadingMetrics, setLoadingMetrics] = useState(true)

  useEffect(() => {
    let mounted = true

    const load = async () => {
      setLoadingMetrics(true)
      try {
        const data = await researchersService.getModelMetrics()
        if (mounted) setMetrics(data)
      } catch {
        if (mounted) setMetrics(null)
      } finally {
        if (mounted) setLoadingMetrics(false)
      }
    }

    load()
    return () => {
      mounted = false
    }
  }, [])

  const distributionData = useMemo(() => {
    const tiers = stats?.tier_distribution || { HIGH: 0, MEDIUM: 0, LOW: 0 }
    return [
      { range: 'HIGH', count: tiers.HIGH || 0 },
      { range: 'MEDIUM', count: tiers.MEDIUM || 0 },
      { range: 'LOW', count: tiers.LOW || 0 },
    ]
  }, [stats])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Model Scoring</h1>
          <p className="text-muted-foreground">Inspect trained model metrics and current score distribution.</p>
        </div>
        <Button onClick={rescoreAll} disabled={isRescoring}>
          <RefreshCw className={`mr-2 h-4 w-4 ${isRescoring ? 'animate-spin' : ''}`} />
          {isRescoring ? 'Rescoring…' : 'Rescore All Researchers'}
        </Button>
      </div>

      <Tabs defaultValue="metrics" className="space-y-4">
        <TabsList>
          <TabsTrigger value="metrics">Model Metrics</TabsTrigger>
          <TabsTrigger value="distribution">Score Distribution</TabsTrigger>
        </TabsList>

        <TabsContent value="metrics">
          <ModelMetricsDashboard metrics={metrics} isLoading={loadingMetrics} />
        </TabsContent>

        <TabsContent value="distribution">
          <Card>
            <CardHeader>
              <CardTitle>Current score distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <ScoreDistributionChart data={distributionData} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
