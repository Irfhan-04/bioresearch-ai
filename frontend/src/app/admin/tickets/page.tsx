'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/use-toast'
import { apiClient } from '@/lib/api/client'

interface Ticket {
  id: string
  subject: string
  body: string
  priority: 'low' | 'medium' | 'high'
  status: 'open' | 'in_progress' | 'resolved' | 'closed'
  user_email: string
  created_at: string
  admin_notes: string | null
}

const PRIORITY_COLORS = {
  low: 'bg-gray-100 text-gray-600',
  medium: 'bg-amber-100 text-amber-700',
  high: 'bg-red-100 text-red-700',
}

const STATUS_COLORS = {
  open: 'bg-blue-100 text-blue-700',
  in_progress: 'bg-amber-100 text-amber-700',
  resolved: 'bg-green-100 text-green-800',
  closed: 'bg-gray-100 text-gray-600',
}

export default function AdminTicketsPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState<string>('open')

  const { data: tickets = [], isLoading } = useQuery<Ticket[]>({
    queryKey: ['admin', 'tickets', statusFilter],
    queryFn: () =>
      apiClient
        .get('/admin/tickets', { params: { status: statusFilter || undefined } })
        .then((r) => r.data),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      apiClient.patch(`/admin/tickets/${id}`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'tickets'] })
      toast({ title: 'Ticket updated' })
    },
    onError: () => toast({ title: 'Failed to update ticket', variant: 'destructive' }),
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Support tickets</h1>
          <p className="mt-1 text-muted-foreground">{tickets.length} ticket{tickets.length !== 1 ? 's' : ''}</p>
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="open">Open</SelectItem>
            <SelectItem value="in_progress">In progress</SelectItem>
            <SelectItem value="resolved">Resolved</SelectItem>
            <SelectItem value="closed">Closed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-32" />)}
        </div>
      ) : tickets.length === 0 ? (
        <p className="text-sm text-muted-foreground py-8 text-center">No tickets found.</p>
      ) : (
        <div className="space-y-3">
          {tickets.map((ticket) => (
            <Card key={ticket.id}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <CardTitle className="text-sm font-medium">{ticket.subject}</CardTitle>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {ticket.user_email} · {new Date(ticket.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    <Badge className={PRIORITY_COLORS[ticket.priority]}>{ticket.priority}</Badge>
                    <Badge className={STATUS_COLORS[ticket.status]}>{ticket.status.replace('_', ' ')}</Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground line-clamp-2">{ticket.body}</p>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Mark as:</span>
                  {(['open', 'in_progress', 'resolved', 'closed'] as const).map((s) => (
                    <Button
                      key={s}
                      size="sm"
                      variant={ticket.status === s ? 'default' : 'outline'}
                      className="h-7 text-xs"
                      onClick={() => updateMutation.mutate({ id: ticket.id, status: s })}
                      disabled={ticket.status === s || updateMutation.isPending}
                    >
                      {s.replace('_', ' ')}
                    </Button>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
