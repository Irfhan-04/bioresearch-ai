'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { pipelinesService } from '@/lib/api/pipelines-service'
import { useToast } from '@/components/ui/use-toast'

export function usePipelines() {
  const { toast } = useToast()
  const qc = useQueryClient()

  const query = useQuery({
    queryKey: ['pipelines'],
    queryFn: pipelinesService.getPipelines,
  })

  const createMutation = useMutation({
    mutationFn: pipelinesService.createPipeline,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pipelines'] })
      toast({ title: 'Pipeline created' })
    },
    onError: () => toast({ title: 'Error', description: 'Failed to create pipeline', variant: 'destructive' }),
  })

  const deleteMutation = useMutation({
    mutationFn: pipelinesService.deletePipeline,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pipelines'] })
      toast({ title: 'Pipeline deleted' })
    },
    onError: () => toast({ title: 'Error', description: 'Failed to delete pipeline', variant: 'destructive' }),
  })

  const runMutation = useMutation({
    mutationFn: pipelinesService.runPipeline,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pipelines'] })
      toast({ title: 'Pipeline started' })
    },
    onError: () => toast({ title: 'Error', description: 'Failed to run pipeline', variant: 'destructive' }),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      active ? pipelinesService.activatePipeline(id) : pipelinesService.pausePipeline(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipelines'] }),
  })

  const fromTemplateMutation = useMutation({
    mutationFn: ({ key, name }: { key: string; name?: string }) => pipelinesService.createFromTemplate(key, name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pipelines'] })
      toast({ title: 'Pipeline created from template' })
    },
    onError: () => toast({ title: 'Error', description: 'Failed to apply template', variant: 'destructive' }),
  })

  const { data: templates } = useQuery({
    queryKey: ['pipeline-templates'],
    queryFn: pipelinesService.getTemplates,
  })

  return {
    pipelines: query.data || [],
    templates: templates || [],
    isLoading: query.isLoading,
    createPipeline: (d: any) => createMutation.mutate(d),
    deletePipeline: (id: string) => deleteMutation.mutate(id),
    runPipeline: (id: string) => runMutation.mutate(id),
    togglePipeline: (id: string, active: boolean) => toggleMutation.mutate({ id, active }),
    createFromTemplate: (key: string, name?: string) => fromTemplateMutation.mutate({ key, name }),
    isRunning: runMutation.isPending,
  }
}
