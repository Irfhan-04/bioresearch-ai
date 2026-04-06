'use client'

import { useRouter } from 'next/navigation'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/use-toast'
import { apiClient } from '@/lib/api/client'

const schema = z.object({
  name: z.string().min(2).max(64),
  description: z.string().max(256).optional(),
})
type FormData = z.infer<typeof schema>

export default function TeamSettingsPage({ params }: { params: { teamId: string } }) {
  const { teamId } = params
  const router = useRouter()
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const { data: team, isLoading } = useQuery({
    queryKey: ['team', teamId],
    queryFn: () => apiClient.get(`/teams/${teamId}`).then((r) => r.data),
  })

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    values: { name: team?.name ?? '', description: team?.description ?? '' },
  })

  const updateMutation = useMutation({
    mutationFn: (data: FormData) =>
      apiClient.put(`/teams/${teamId}`, data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team', teamId] })
      toast({ title: 'Team updated' })
    },
    onError: () => {
      toast({ title: 'Update failed', variant: 'destructive' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => apiClient.delete(`/teams/${teamId}`),
    onSuccess: () => {
      toast({ title: 'Team deleted' })
      router.push('/teams')
    },
    onError: () => {
      toast({ title: 'Only the team owner can delete this team.', variant: 'destructive' })
    },
  })

  if (isLoading) return <Skeleton className="h-64" />

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Team settings</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">General</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={handleSubmit((data) => updateMutation.mutate(data))}
            className="space-y-4"
          >
            <div className="space-y-1">
              <Label htmlFor="name">Team name</Label>
              <Input id="name" {...register('name')} />
              {errors.name && (
                <p className="text-xs text-destructive">{errors.name.message}</p>
              )}
            </div>

            <div className="space-y-1">
              <Label htmlFor="description">Description</Label>
              <Input id="description" {...register('description')} />
            </div>

            <Button type="submit" disabled={updateMutation.isPending}>
              {updateMutation.isPending ? 'Saving...' : 'Save changes'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="text-base text-destructive">Danger zone</CardTitle>
          <CardDescription>
            Deleting the team is permanent and cannot be undone.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            variant="destructive"
            onClick={() => {
              if (confirm('Delete this team permanently? This cannot be undone.')) {
                deleteMutation.mutate()
              }
            }}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? 'Deleting...' : 'Delete team'}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
