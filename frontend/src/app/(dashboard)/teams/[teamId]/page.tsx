'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { Settings, Users } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { apiClient } from '@/lib/api/client'

interface Team {
  id: string
  name: string
  description: string | null
  slug: string
  owner_id: string
  member_count: number
  created_at: string
}

export default function TeamOverviewPage({ params }: { params: { teamId: string } }) {
  const { teamId } = params

  const { data: team, isLoading } = useQuery<Team>({
    queryKey: ['team', teamId],
    queryFn: () => apiClient.get(`/teams/${teamId}`).then((r) => r.data),
  })

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      </div>
    )
  }

  if (!team) return <p className="text-muted-foreground">Team not found.</p>

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{team.name}</h1>
          {team.description && (
            <p className="mt-1 text-muted-foreground">{team.description}</p>
          )}
          <Badge variant="outline" className="mt-2 font-mono text-xs">
            {team.slug}
          </Badge>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href={`/teams/${teamId}/members`}>
              <Users className="mr-2 h-4 w-4" />
              Members
            </Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link href={`/teams/${teamId}/settings`}>
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Members</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">{team.member_count}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Created</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-medium">
              {new Date(team.created_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Quick links</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <Button variant="link" size="sm" className="h-auto p-0 text-sm" asChild>
              <Link href={`/teams/${teamId}/members`}>Manage members</Link>
            </Button>
            <br />
            <Button variant="link" size="sm" className="h-auto p-0 text-sm" asChild>
              <Link href={`/teams/${teamId}/settings`}>Edit team settings</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
