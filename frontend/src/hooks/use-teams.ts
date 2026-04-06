'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { teamsService } from '@/lib/api/teams-service'
import { useToast } from '@/components/ui/use-toast'

export function useTeams() {
  const { toast } = useToast()
  const qc = useQueryClient()

  const query = useQuery({ queryKey: ['teams'], queryFn: teamsService.getTeams })

  const createMutation = useMutation({
    mutationFn: teamsService.createTeam,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['teams'] })
      toast({ title: 'Team created' })
    },
    onError: () => toast({ title: 'Error', description: 'Failed to create team', variant: 'destructive' }),
  })

  const deleteMutation = useMutation({
    mutationFn: teamsService.deleteTeam,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['teams'] })
      toast({ title: 'Team deleted' })
    },
  })

  const inviteMutation = useMutation({
    mutationFn: ({ teamId, data }: { teamId: string; data: any }) => teamsService.inviteMember(teamId, data),
    onSuccess: () => toast({ title: 'Invitation sent' }),
    onError: () => toast({ title: 'Error', description: 'Failed to invite member', variant: 'destructive' }),
  })

  return {
    teams: query.data || [],
    isLoading: query.isLoading,
    createTeam: (d: any) => createMutation.mutate(d),
    deleteTeam: (id: string) => deleteMutation.mutate(id),
    inviteMember: (teamId: string, d: any) => inviteMutation.mutate({ teamId, data: d }),
    refetch: query.refetch,
  }
}

export function useTeamMembers(teamId: string) {
  return useQuery({
    queryKey: ['team-members', teamId],
    queryFn: () => teamsService.getMembers(teamId),
    enabled: !!teamId,
  })
}
