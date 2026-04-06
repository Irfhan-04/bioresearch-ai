'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { scoringService } from '@/lib/api/scoring-service'
import { useToast } from '@/components/ui/use-toast'

export function useScoring() {
  const { toast } = useToast()
  const qc = useQueryClient()

  const config = useQuery({ queryKey: ['scoring-config'], queryFn: scoringService.getConfig })
  const stats = useQuery({ queryKey: ['scoring-stats'], queryFn: scoringService.getStats })

  const updateConfigMutation = useMutation({
    mutationFn: scoringService.updateConfig,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['scoring-config'] })
      toast({ title: 'Weights saved' })
    },
  })

  const rescoreAllMutation = useMutation({
    mutationFn: scoringService.rescoreAll,
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['leads'] })
      qc.invalidateQueries({ queryKey: ['scoring-stats'] })
      toast({ title: `Rescored ${r.leads_rescored} leads`, description: `Avg score: ${r.average_score}` })
    },
    onError: () => toast({ title: 'Error', description: 'Rescore failed', variant: 'destructive' }),
  })

  return {
    config: config.data,
    stats: stats.data,
    isLoading: config.isLoading,
    updateConfig: (w: any) => updateConfigMutation.mutate(w),
    rescoreAll: () => rescoreAllMutation.mutate(),
    isRescoring: rescoreAllMutation.isPending,
  }
}
