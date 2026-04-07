'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api/client'
import { CreateResearcherRequest, Researcher, ResearcherFilters } from '@/types/researcher'
import { useToast } from '@/components/ui/use-toast'

const toResearcher = (r: any): Researcher => ({
  ...r,
  relevance_score: r.relevance_score ?? r.propensity_score ?? null,
  relevance_tier: r.relevance_tier ?? r.priority_tier ?? 'UNSCORED',
})


export function useResearchers(filters?: ResearcherFilters) {
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const researchersQuery = useQuery({
    queryKey: ['researchers', filters],
    queryFn: async () => {
      const data = (await apiClient.get('/researchers', { params: filters })).data
      return { ...data, items: (data?.items || []).map(toResearcher) }
    },
  })

  const createMutation = useMutation({
    mutationFn: async (data: CreateResearcherRequest) => (await apiClient.post('/researchers', data)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['researchers'] })
      toast({ title: 'Researcher created' })
    },
    onError: () => toast({ title: 'Error', description: 'Failed to create researcher', variant: 'destructive' }),
  })

  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<Researcher> }) =>
      (await apiClient.put(`/researchers/${id}`, data)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['researchers'] })
      toast({ title: 'Researcher updated' })
    },
    onError: () => toast({ title: 'Error', description: 'Failed to update researcher', variant: 'destructive' }),
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => (await apiClient.delete(`/researchers/${id}`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['researchers'] })
      toast({ title: 'Researcher deleted' })
    },
    onError: () => toast({ title: 'Error', description: 'Failed to delete researcher', variant: 'destructive' }),
  })

  return {
    researchers: researchersQuery.data?.items || [],
    total: researchersQuery.data?.pagination?.total || 0,
    pages: researchersQuery.data?.pagination?.pages || 0,
    isLoading: researchersQuery.isLoading,
    isError: researchersQuery.isError,
    createResearcher: (d: CreateResearcherRequest) => createMutation.mutate(d),
    updateResearcher: (id: string, data: Partial<Researcher>) => updateMutation.mutate({ id, data }),
    updateResearcherAsync: (id: string, data: Partial<Researcher>) => updateMutation.mutateAsync({ id, data }),
    deleteResearcher: (id: string) => deleteMutation.mutate(id),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    refetch: researchersQuery.refetch,
  }
}

export function useResearcher(id: string) {
  return useQuery({
    queryKey: ['researcher', id],
    queryFn: async () => toResearcher((await apiClient.get(`/researchers/${id}`)).data),
    enabled: !!id,
  })
}
