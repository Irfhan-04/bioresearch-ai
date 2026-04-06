'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { leadsService } from '@/lib/api/leads-service'
import { Lead, LeadFilters, CreateLeadRequest } from '@/types/lead'
import { useToast } from '@/components/ui/use-toast'

export function useLeads(filters?: LeadFilters) {
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const leadsQuery = useQuery({
    queryKey: ['leads', filters],
    queryFn: () => leadsService.getLeads(filters),
  })

  const createMutation = useMutation({
    mutationFn: leadsService.createLead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      toast({ title: 'Lead created' })
    },
    onError: () => toast({ title: 'Error', description: 'Failed to create lead', variant: 'destructive' }),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Lead> }) => leadsService.updateLead(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      toast({ title: 'Lead updated' })
    },
    onError: () => toast({ title: 'Error', description: 'Failed to update lead', variant: 'destructive' }),
  })

  const deleteMutation = useMutation({
    mutationFn: leadsService.deleteLead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      toast({ title: 'Lead deleted' })
    },
    onError: () => toast({ title: 'Error', description: 'Failed to delete lead', variant: 'destructive' }),
  })

  return {
    leads: leadsQuery.data?.items || [],
    total: leadsQuery.data?.pagination.total || 0,
    pages: leadsQuery.data?.pagination.pages || 0,
    isLoading: leadsQuery.isLoading,
    isError: leadsQuery.isError,
    createLead: (d: CreateLeadRequest) => createMutation.mutate(d),
    updateLead: (id: string, data: Partial<Lead>) => updateMutation.mutate({ id, data }),
    updateLeadAsync: (id: string, data: Partial<Lead>) => updateMutation.mutateAsync({ id, data }),
    deleteLead: (id: string) => deleteMutation.mutate(id),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    refetch: leadsQuery.refetch,
  }
}

export function useLead(id: string) {
  return useQuery({
    queryKey: ['lead', id],
    queryFn: () => leadsService.getLead(id),
    enabled: !!id,
  })
}
