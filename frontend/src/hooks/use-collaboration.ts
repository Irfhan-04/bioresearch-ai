'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { collaborationService } from '@/lib/api/collaboration-service'
import { useToast } from '@/components/ui/use-toast'

export function useActivities(leadId: string) {
  const { toast } = useToast()
  const qc = useQueryClient()

  const query = useQuery({
    queryKey: ['activities', leadId],
    queryFn: () => collaborationService.getActivities(leadId),
    enabled: !!leadId,
  })

  const addMutation = useMutation({
    mutationFn: (data: any) => collaborationService.addActivity(leadId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['activities', leadId] })
      toast({ title: 'Added' })
    },
    onError: () => toast({ title: 'Error', variant: 'destructive' }),
  })

  const statusMutation = useMutation({
    mutationFn: (status: string) => collaborationService.changeStatus(leadId, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lead', leadId] })
      qc.invalidateQueries({ queryKey: ['activities', leadId] })
    },
  })

  return {
    activities: query.data || [],
    isLoading: query.isLoading,
    addActivity: (d: any) => addMutation.mutate(d),
    changeStatus: (s: string) => statusMutation.mutate(s),
    isAdding: addMutation.isPending,
  }
}

export function useReminders(dueWithinDays = 7) {
  const { toast } = useToast()
  const qc = useQueryClient()

  const query = useQuery({
    queryKey: ['reminders', dueWithinDays],
    queryFn: () => collaborationService.getReminders(dueWithinDays),
  })

  const doneMutation = useMutation({
    mutationFn: collaborationService.completeReminder,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reminders'] })
      toast({ title: 'Reminder completed' })
    },
  })

  return {
    reminders: query.data || [],
    isLoading: query.isLoading,
    completeReminder: (id: string) => doneMutation.mutate(id),
  }
}
