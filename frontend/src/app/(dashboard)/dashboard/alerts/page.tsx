'use client'

import { useState } from 'react'
import { Plus, Trash, Play, Bell, BellOff } from 'lucide-react'
import { useAlerts } from '@/hooks/use-alerts'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'

const TRIGGER_LABELS: Record<string, string> = {
  high_value_lead: 'High-Value Lead',
  new_nih_grant: 'New NIH Grant',
  conference_match: 'Conference Match',
  score_increase: 'Score Increase',
}

export default function AlertsPage() {
  const { alerts, isLoading, createAlert, updateAlert, deleteAlert, testAlert, isTesting } = useAlerts()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ name: '', trigger: 'high_value_lead', channel: 'email', min_score: '75' })

  const handleCreate = () => {
    createAlert({
      name: form.name,
      trigger: form.trigger,
      channel: form.channel,
      conditions: form.trigger === 'high_value_lead' ? { min_score: Number(form.min_score) } : {},
    })
    setOpen(false)
    setForm({ name: '', trigger: 'high_value_lead', channel: 'email', min_score: '75' })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Smart Alerts</h1>
          <p className="text-muted-foreground">Get notified when high-value leads are discovered</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New Alert Rule
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Alert Rule</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-1">
                <Label>Rule Name</Label>
                <Input
                  placeholder="e.g. High-value NIH leads"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                />
              </div>
              <div className="space-y-1">
                <Label>Trigger</Label>
                <Select value={form.trigger} onValueChange={(v) => setForm((f) => ({ ...f, trigger: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(TRIGGER_LABELS).map(([v, l]) => (
                      <SelectItem key={v} value={v}>
                        {l}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {form.trigger === 'high_value_lead' && (
                <div className="space-y-1">
                  <Label>Minimum Score</Label>
                  <Input
                    type="number"
                    min="0"
                    max="100"
                    value={form.min_score}
                    onChange={(e) => setForm((f) => ({ ...f, min_score: e.target.value }))}
                  />
                </div>
              )}
              <div className="space-y-1">
                <Label>Notify via</Label>
                <Select value={form.channel} onValueChange={(v) => setForm((f) => ({ ...f, channel: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="email">Email</SelectItem>
                    <SelectItem value="webhook">Webhook</SelectItem>
                    <SelectItem value="both">Both</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button className="w-full" disabled={!form.name} onClick={handleCreate}>
                Create Rule
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-lg" />
          ))}
        </div>
      ) : alerts.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <Bell className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
            <p className="text-lg font-medium">No alert rules yet</p>
            <p className="text-sm text-muted-foreground">Create rules to be notified about high-value leads</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {alerts.map((a: any) => (
            <Card key={a.id}>
              <CardContent className="flex items-center justify-between py-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{a.name}</span>
                    <Badge variant={a.is_active ? 'default' : 'outline'}>{a.is_active ? 'Active' : 'Paused'}</Badge>
                  </div>
                  <div className="flex gap-3 text-xs text-muted-foreground">
                    <span>{TRIGGER_LABELS[a.trigger] || a.trigger}</span>
                    <span>·</span>
                    <span className="capitalize">via {a.channel}</span>
                    <span>·</span>
                    <span>Fired {a.trigger_count} times</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="outline" disabled={isTesting} onClick={() => testAlert(a.id)}>
                    <Play className="mr-1 h-3 w-3" />
                    Test
                  </Button>
                  <Button size="icon" variant="ghost" onClick={() => updateAlert(a.id, { is_active: !a.is_active })}>
                    {a.is_active ? <BellOff className="h-4 w-4" /> : <Bell className="h-4 w-4" />}
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="text-destructive"
                    onClick={() => confirm('Delete alert?') && deleteAlert(a.id)}
                  >
                    <Trash className="h-4 w-4" />
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
