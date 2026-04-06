'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/use-toast'
import { apiClient } from '@/lib/api/client'

interface FeatureFlag {
  key: string
  enabled: boolean
  description: string | null
  updated_at: string
}

export default function AdminFlagsPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const { data: flags = [], isLoading } = useQuery<FeatureFlag[]>({
    queryKey: ['admin', 'flags'],
    queryFn: () => apiClient.get('/admin/flags').then((r) => r.data),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ key, enabled }: { key: string; enabled: boolean }) =>
      apiClient.put(`/admin/flags/${key}`, { enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'flags'] })
      toast({ title: 'Feature flag updated' })
    },
    onError: () => toast({ title: 'Failed to update flag', variant: 'destructive' }),
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Feature flags</h1>
        <p className="mt-1 text-muted-foreground">
          Toggle features on or off without a deployment.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-20" />)}
        </div>
      ) : flags.length === 0 ? (
        <p className="text-sm text-muted-foreground">No feature flags configured yet.</p>
      ) : (
        <div className="space-y-3">
          {flags.map((flag) => (
            <Card key={flag.key} className="flex items-center justify-between p-4">
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <code className="text-sm font-mono font-medium">{flag.key}</code>
                  <Badge className={flag.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}>
                    {flag.enabled ? 'enabled' : 'disabled'}
                  </Badge>
                </div>
                {flag.description && (
                  <p className="text-xs text-muted-foreground mt-0.5">{flag.description}</p>
                )}
              </div>
              <button
                onClick={() => toggleMutation.mutate({ key: flag.key, enabled: !flag.enabled })}
                disabled={toggleMutation.isPending}
                className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none ${
                  flag.enabled ? 'bg-blue-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    flag.enabled ? 'translate-x-4' : 'translate-x-0'
                  }`}
                />
              </button>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
