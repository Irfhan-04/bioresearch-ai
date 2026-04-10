'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ModelMetrics } from '@/lib/api/researchers-service'

interface Props {
  metrics: ModelMetrics | null
  isLoading?: boolean
}

export function ModelMetricsDashboard({ metrics, isLoading = false }: Props) {
  if (isLoading) return <div className="text-sm text-muted-foreground">Loading model metrics…</div>
  if (!metrics) return <div className="text-sm text-muted-foreground">Model metrics unavailable. Train model to generate eval_v1.json.</div>

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Model Overview</CardTitle></CardHeader>
        <CardContent className="grid gap-3 text-sm md:grid-cols-3">
          <div>Type: <span className="font-medium">{metrics.model_type}</span></div>
          <div>Last Trained: <span className="font-medium">{new Date(metrics.trained_at).toLocaleDateString()}</span></div>
          <div>Sample Count: <span className="font-medium">{metrics.n_training_samples}</span></div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Classification Performance</CardTitle></CardHeader>
        <CardContent className="grid gap-3 text-sm md:grid-cols-2">
          <div>Accuracy: <span className="font-medium">{pct(metrics.test_accuracy)}</span></div>
          <div>Macro F1: <span className="font-medium">{pct(metrics.macro_f1)}</span></div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Per-Class Metrics</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {Object.entries(metrics.per_class || {}).map(([label, values]) => (
            <div key={label} className="rounded border p-3">
              <div className="mb-2 flex items-center justify-between"><Badge variant="outline">{label}</Badge></div>
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
        <CardHeader><CardTitle>Confusion Matrix</CardTitle></CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {metrics.confusion_matrix?.length ? JSON.stringify(metrics.confusion_matrix) : 'No confusion matrix available.'}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Feature Importances</CardTitle></CardHeader>
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

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`
}
