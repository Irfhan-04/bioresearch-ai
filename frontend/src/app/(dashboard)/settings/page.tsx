'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/use-toast'
import { apiClient } from '@/lib/api/client'

const profileSchema = z.object({
  full_name: z.string().min(1, 'Name is required').max(128),
  email: z.string().email(),
})
const passwordSchema = z.object({
  current_password: z.string().min(6),
  new_password: z.string().min(8, 'At least 8 characters'),
})
type ProfileForm = z.infer<typeof profileSchema>
type PasswordForm = z.infer<typeof passwordSchema>

export default function SettingsPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const { data: me, isLoading } = useQuery({
    queryKey: ['user', 'me'],
    queryFn: () => apiClient.get('/users/me').then((r) => r.data),
  })

  const { register: regProfile, handleSubmit: submitProfile, formState: { errors: pe } } =
    useForm<ProfileForm>({
      resolver: zodResolver(profileSchema),
      values: { full_name: me?.full_name ?? '', email: me?.email ?? '' },
    })

  const { register: regPwd, handleSubmit: submitPwd, reset: resetPwd, formState: { errors: we } } =
    useForm<PasswordForm>({ resolver: zodResolver(passwordSchema) })

  const profileMutation = useMutation({
    mutationFn: (data: ProfileForm) => apiClient.put('/users/me', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user', 'me'] })
      toast({ title: 'Profile updated' })
    },
    onError: () => toast({ title: 'Update failed', variant: 'destructive' }),
  })

  const passwordMutation = useMutation({
    mutationFn: (data: PasswordForm) => apiClient.put('/users/me/password', data),
    onSuccess: () => {
      resetPwd()
      toast({ title: 'Password changed' })
    },
    onError: () => toast({ title: 'Incorrect current password', variant: 'destructive' }),
  })

  if (isLoading) return <Skeleton className="h-64 w-full max-w-lg" />

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Settings</h1>

      <Card>
        <CardHeader><CardTitle className="text-base">Profile</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={submitProfile((d) => profileMutation.mutate(d))} className="space-y-4">
            <div className="space-y-1">
              <Label>Full name</Label>
              <Input {...regProfile('full_name')} />
              {pe.full_name && <p className="text-xs text-destructive">{pe.full_name.message}</p>}
            </div>
            <div className="space-y-1">
              <Label>Email</Label>
              <Input type="email" {...regProfile('email')} />
              {pe.email && <p className="text-xs text-destructive">{pe.email.message}</p>}
            </div>
            <Button type="submit" disabled={profileMutation.isPending}>
              {profileMutation.isPending ? 'Saving...' : 'Save profile'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Change password</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={submitPwd((d) => passwordMutation.mutate(d))} className="space-y-4">
            <div className="space-y-1">
              <Label>Current password</Label>
              <Input type="password" {...regPwd('current_password')} />
              {we.current_password && <p className="text-xs text-destructive">{we.current_password.message}</p>}
            </div>
            <div className="space-y-1">
              <Label>New password</Label>
              <Input type="password" {...regPwd('new_password')} />
              {we.new_password && <p className="text-xs text-destructive">{we.new_password.message}</p>}
            </div>
            <Button type="submit" disabled={passwordMutation.isPending}>
              {passwordMutation.isPending ? 'Changing...' : 'Change password'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}