'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ModelMetrics } from '@/lib/api/researchers-service'

interface Props {
  metrics: ModelMetrics | null
  isLoading?: boolean
}

export function ModelMetricsDashboard({ metrics, isLoading = false }: Props) {
  if (isLoading) {
    return <div className="text-sm text-muted-foreground">Loading model metrics…</div>
  }

  if (!metrics) {
    return <div className="text-sm text-muted-foreground">Model metrics unavailable. Train model to generate eval_v1.json.</div>
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Model" value={metrics.model_type} />
        <StatCard label="Accuracy" value={pct(metrics.test_accuracy)} />
        <StatCard label="Macro F1" value={pct(metrics.macro_f1)} />
        <StatCard label="Test Samples" value={String(metrics.n_test_samples)} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Per-class performance</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {Object.entries(metrics.per_class || {}).map(([label, values]) => (
            <div key={label} className="rounded border p-3">
              <div className="mb-2 flex items-center justify-between">
                <Badge variant="outline">{label}</Badge>
              </div>
              <div className="grid grid-cols-3 gap-2 text-sm">
                <div>Precision: <span className="font-medium">{pct(values.precision)}</span></div>
                <div>Recall: <span className="font-medium">{pct(values.recall)}</span></div>
                <div>F1: <span className="font-medium">{pct(values.f1)}</span></div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Top feature importance</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {metrics.top_10_features?.map((feature) => (
            <div key={feature.feature} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
              <span>{feature.display_name}</span>
              <span className="font-mono text-xs text-muted-foreground">{feature.importance.toFixed(6)}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm text-muted-foreground">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold">{value}</div>
      </CardContent>
    </Card>
  )
}

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`
}
