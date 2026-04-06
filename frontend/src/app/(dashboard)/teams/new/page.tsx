'use client'

import { useRouter } from 'next/navigation'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/components/ui/use-toast'
import { apiClient } from '@/lib/api/client'

const schema = z.object({
  name: z.string().min(2, 'Team name must be at least 2 characters').max(64),
  description: z.string().max(256).optional(),
})
type FormData = z.infer<typeof schema>

export default function NewTeamPage() {
  const router = useRouter()
  const { toast } = useToast()

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      apiClient.post('/teams/', data).then((r) => r.data),
    onSuccess: (team) => {
      toast({ title: 'Team created', description: `"${team.name}" is ready.` })
      router.push(`/teams/${team.id}`)
    },
    onError: () => {
      toast({ title: 'Failed to create team', variant: 'destructive' })
    },
  })

  return (
    <div className="max-w-lg space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Create a team</h1>
        <p className="mt-1 text-muted-foreground">
          Invite colleagues to collaborate on leads.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Team details</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={handleSubmit((data) => mutation.mutate(data))}
            className="space-y-4"
          >
            <div className="space-y-1">
              <Label htmlFor="name">Team name</Label>
              <Input id="name" placeholder="e.g. BD West Coast" {...register('name')} />
              {errors.name && (
                <p className="text-xs text-destructive">{errors.name.message}</p>
              )}
            </div>

            <div className="space-y-1">
              <Label htmlFor="description">Description (optional)</Label>
              <Input
                id="description"
                placeholder="What is this team focused on?"
                {...register('description')}
              />
            </div>

            <div className="flex gap-3 pt-2">
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? 'Creating...' : 'Create team'}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => router.back()}
              >
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
