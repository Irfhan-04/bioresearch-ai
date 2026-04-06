'use client'

import { useState } from 'react'
import { CheckCircle, Clock, MessageSquare, User } from 'lucide-react'
import { useReminders } from '@/hooks/use-collaboration'
import { useLeads } from '@/hooks/use-leads'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export default function CollaborationPage() {
  const { reminders, isLoading: remLoading, completeReminder } = useReminders(14)
  const { leads, isLoading: leadsLoading } = useLeads({ status: 'CONTACTED', size: 10 })
  const [tab, setTab] = useState<'reminders' | 'assigned'>('reminders')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Collaboration</h1>
        <p className="text-muted-foreground">Reminders, notes, and lead assignments</p>
      </div>

      <div className="flex gap-2">
        <Button variant={tab === 'reminders' ? 'default' : 'outline'} onClick={() => setTab('reminders')}>
          <Clock className="mr-2 h-4 w-4" />
          Reminders
          {reminders.length > 0 && (
            <Badge variant="secondary" className="ml-2">
              {reminders.length}
            </Badge>
          )}
        </Button>
        <Button variant={tab === 'assigned' ? 'default' : 'outline'} onClick={() => setTab('assigned')}>
          <User className="mr-2 h-4 w-4" />
          Recently Contacted
        </Button>
      </div>

      {tab === 'reminders' && (
        <div className="space-y-3">
          {remLoading ? (
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)
          ) : reminders.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Clock className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
                <p className="font-medium">No upcoming reminders</p>
                <p className="text-sm text-muted-foreground">Add reminders from any lead&apos;s activity feed</p>
              </CardContent>
            </Card>
          ) : (
            reminders.map((r: any) => (
              <Card key={r.id}>
                <CardContent className="flex items-center justify-between py-3">
                  <div className="space-y-0.5">
                    <p className="text-sm font-medium">{r.content}</p>
                    <p className="text-xs text-muted-foreground">Due: {new Date(r.reminder_due_at).toLocaleString()}</p>
                  </div>
                  <Button size="sm" variant="outline" onClick={() => completeReminder(r.id)}>
                    <CheckCircle className="mr-1 h-4 w-4" />
                    Done
                  </Button>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {tab === 'assigned' && (
        <div className="space-y-3">
          {leadsLoading ? (
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)
          ) : leads.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <MessageSquare className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
                <p className="font-medium">No contacted leads</p>
              </CardContent>
            </Card>
          ) : (
            leads.map((lead: any) => (
              <Card key={lead.id}>
                <CardContent className="flex items-center justify-between py-3">
                  <div>
                    <p className="text-sm font-medium">{lead.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {lead.company} · {lead.title}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{lead.status}</Badge>
                    <Badge variant={lead.propensity_score >= 70 ? 'default' : 'secondary'}>{lead.propensity_score}</Badge>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}
    </div>
  )
}
