'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useMutation } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'

import { useToast } from '@/components/ui/use-toast'
import { apiClient } from '@/lib/api/client'

export default function InviteTokenPage({ params }: { params: { token: string } }) {
  const router = useRouter()
  const { toast } = useToast()

  const { mutate } = useMutation({
    mutationFn: () =>
      apiClient.get(`/teams/invitations/accept/${params.token}`).then((r) => r.data),
    onSuccess: (data) => {
      toast({ title: 'You have joined the team', description: data?.message })
      router.push('/teams')
    },
    onError: () => {
      toast({
        title: 'Invalid or expired invitation',
        description: 'This invite link may have already been used or has expired.',
        variant: 'destructive',
      })
      router.push('/dashboard')
    },
  })

  useEffect(() => {
    mutate()
  }, [mutate])

  return (
    <div className="flex h-64 items-center justify-center">
      <div className="flex flex-col items-center gap-3 text-muted-foreground">
        <Loader2 className="h-8 w-8 animate-spin" />
        <p className="text-sm">Accepting invitation...</p>
      </div>
    </div>
  )
}
