'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { alertsService } from '@/lib/api/alerts-service'
import { useToast } from '@/components/ui/use-toast'

export function useAlerts() {
  const { toast } = useToast()
  const qc = useQueryClient()

  const query = useQuery({ queryKey: ['alerts'], queryFn: alertsService.getAlerts })

  const createMutation = useMutation({
    mutationFn: alertsService.createAlert,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] })
      toast({ title: 'Alert rule created' })
    },
    onError: () => toast({ title: 'Error', description: 'Failed to create alert', variant: 'destructive' }),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => alertsService.updateAlert(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: alertsService.deleteAlert,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] })
      toast({ title: 'Alert deleted' })
    },
  })

  const testMutation = useMutation({
    mutationFn: alertsService.testAlert,
    onSuccess: (r) => toast({ title: r.fired ? '✅ Alert fired!' : 'No matching leads', description: r.message }),
    onError: () => toast({ title: 'Error', description: 'Test failed', variant: 'destructive' }),
  })

  return {
    alerts: query.data || [],
    isLoading: query.isLoading,
    createAlert: (d: any) => createMutation.mutate(d),
    updateAlert: (id: string, d: any) => updateMutation.mutate({ id, data: d }),
    deleteAlert: (id: string) => deleteMutation.mutate(id),
    testAlert: (id: string) => testMutation.mutate(id),
    isTesting: testMutation.isPending,
  }
}
