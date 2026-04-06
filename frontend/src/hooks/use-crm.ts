'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { crmService } from '@/lib/api/crm-service'
import { useToast } from '@/components/ui/use-toast'

export function useCrm() {
  const { toast } = useToast()
  const qc = useQueryClient()

  const query = useQuery({ queryKey: ['crm-connections'], queryFn: crmService.getConnections })

  const createMutation = useMutation({
    mutationFn: crmService.createConnection,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['crm-connections'] })
      toast({ title: 'CRM connected' })
    },
    onError: () => toast({ title: 'Error', description: 'Failed to connect CRM', variant: 'destructive' }),
  })

  const deleteMutation = useMutation({
    mutationFn: crmService.deleteConnection,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['crm-connections'] })
      toast({ title: 'CRM disconnected' })
    },
  })

  const testMutation = useMutation({
    mutationFn: crmService.testConnection,
    onSuccess: (r) => toast({ title: r.ok ? '✅ Connection valid' : '❌ Connection failed', description: r.message }),
  })

  const syncMutation = useMutation({
    mutationFn: ({ id, dryRun }: { id: string; dryRun?: boolean }) => crmService.syncLeads(id, { dry_run: dryRun }),
    onSuccess: (r) =>
      toast({
        title: `Sync ${r.status}`,
        description: `${r.leads_pushed} pushed, ${r.leads_updated} updated, ${r.leads_failed} failed`,
      }),
    onError: () => toast({ title: 'Sync failed', variant: 'destructive' }),
  })

  return {
    connections: query.data || [],
    isLoading: query.isLoading,
    createConnection: (d: any) => createMutation.mutate(d),
    deleteConnection: (id: string) => deleteMutation.mutate(id),
    testConnection: (id: string) => testMutation.mutate(id),
    syncLeads: (id: string, dryRun?: boolean) => syncMutation.mutate({ id, dryRun }),
    isSyncing: syncMutation.isPending,
    isTesting: testMutation.isPending,
  }
}
