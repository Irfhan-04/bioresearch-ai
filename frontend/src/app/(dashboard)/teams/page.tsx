'use client'

import Link from 'next/link'
import { useState } from 'react'
import { Plus, Trash, Users, Settings } from 'lucide-react'
import { useTeams } from '@/hooks/use-teams'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'

export default function TeamsPage() {
  const { teams, isLoading, createTeam, deleteTeam } = useTeams()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')

  const handleCreate = () => {
    if (!name.trim()) return
    createTeam({ name: name.trim() })
    setOpen(false)
    setName('')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Teams</h1>
          <p className="text-muted-foreground">Collaborate with your colleagues on shared lead pools</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New Team
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create a Team</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-1">
                <Label>Team Name</Label>
                <Input
                  placeholder="e.g. East Coast Sales"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                />
              </div>
              <Button className="w-full" disabled={!name.trim()} onClick={handleCreate}>
                Create Team
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : teams.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <Users className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
            <p className="text-lg font-medium">No teams yet</p>
            <p className="mb-4 text-sm text-muted-foreground">Create a team to start collaborating</p>
            <Button onClick={() => setOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create Team
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {teams.map((t: any) => (
            <Card key={t.id}>
              <CardHeader className="flex flex-row items-start justify-between pb-2">
                <div>
                  <CardTitle className="text-base">{t.name}</CardTitle>
                  {t.description && <p className="mt-0.5 text-xs text-muted-foreground">{t.description}</p>}
                </div>
                <Badge variant="outline" className="capitalize">
                  {t.role || 'member'}
                </Badge>
              </CardHeader>
              <CardContent>
                <p className="mb-3 text-sm text-muted-foreground">
                  {t.member_count || 0} members · {t.lead_count || 0} leads
                </p>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" asChild>
                    <Link href={`/teams/${t.id}`}>
                      <Settings className="mr-1 h-3 w-3" />
                      Manage
                    </Link>
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-destructive"
                    onClick={() => confirm('Delete this team?') && deleteTeam(t.id)}
                  >
                    <Trash className="h-3 w-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
