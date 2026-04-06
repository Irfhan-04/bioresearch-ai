'use client'

import { useState } from 'react'
import { Plus, Trash, Play, CheckCircle, XCircle, Link2 } from 'lucide-react'
import { useCrm } from '@/hooks/use-crm'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'

const PROVIDERS = ['hubspot', 'pipedrive', 'salesforce', 'custom']
const PROVIDER_CRED_FIELDS: Record<string, { label: string; key: string }[]> = {
  hubspot: [{ label: 'API Key', key: 'api_key' }],
  pipedrive: [{ label: 'API Token', key: 'api_token' }],
  salesforce: [
    { label: 'Instance URL', key: 'instance_url' },
    { label: 'Access Token', key: 'access_token' },
  ],
  custom: [{ label: 'Webhook URL', key: 'webhook_url' }],
}

export default function CrmPage() {
  const { connections, isLoading, createConnection, deleteConnection, testConnection, syncLeads, isSyncing, isTesting } = useCrm()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<any>({ provider: 'hubspot', name: '', credentials: {} })

  const handleCreate = () => {
    createConnection(form)
    setOpen(false)
    setForm({ provider: 'hubspot', name: '', credentials: {} })
  }

  const credFields = PROVIDER_CRED_FIELDS[form.provider] || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">CRM Integrations</h1>
          <p className="text-muted-foreground">Sync leads to HubSpot, Pipedrive, Salesforce, or a custom webhook</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Connect CRM
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Connect a CRM</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-1">
                <Label>Provider</Label>
                <Select value={form.provider} onValueChange={(v) => setForm((f: any) => ({ ...f, provider: v, credentials: {} }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PROVIDERS.map((p) => (
                      <SelectItem key={p} value={p} className="capitalize">
                        {p}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label>Name</Label>
                <Input
                  placeholder="My HubSpot"
                  value={form.name}
                  onChange={(e) => setForm((f: any) => ({ ...f, name: e.target.value }))}
                />
              </div>
              {credFields.map(({ label, key }) => (
                <div key={key} className="space-y-1">
                  <Label>{label}</Label>
                  <Input
                    type="password"
                    value={form.credentials[key] || ''}
                    onChange={(e) =>
                      setForm((f: any) => ({ ...f, credentials: { ...f.credentials, [key]: e.target.value } }))
                    }
                  />
                </div>
              ))}
              <Button className="w-full" disabled={!form.name} onClick={handleCreate}>
                Connect
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
      ) : connections.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <Link2 className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
            <p className="text-lg font-medium">No CRM connections</p>
            <p className="mb-4 text-sm text-muted-foreground">Connect a CRM to sync leads automatically</p>
            <Button onClick={() => setOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Connect CRM
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {connections.map((c: any) => (
            <Card key={c.id}>
              <CardContent className="flex items-center justify-between py-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{c.name}</span>
                    <Badge variant="outline" className="capitalize">
                      {c.provider}
                    </Badge>
                    <Badge variant={c.is_active ? 'default' : 'outline'}>{c.is_active ? 'Active' : 'Inactive'}</Badge>
                    {c.last_sync_status && (
                      <Badge variant={c.last_sync_status === 'success' ? 'default' : 'destructive'}>
                        {c.last_sync_status === 'success' ? (
                          <CheckCircle className="mr-1 h-3 w-3" />
                        ) : (
                          <XCircle className="mr-1 h-3 w-3" />
                        )}
                        {c.last_sync_status}
                      </Badge>
                    )}
                  </div>
                  <div className="flex gap-3 text-xs text-muted-foreground">
                    <span>{c.total_synced_leads} leads synced</span>
                    {c.last_sync_at && <span>Last sync: {new Date(c.last_sync_at).toLocaleString()}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="outline" disabled={isTesting} onClick={() => testConnection(c.id)}>
                    Test
                  </Button>
                  <Button size="sm" disabled={isSyncing} onClick={() => syncLeads(c.id)}>
                    <Play className="mr-1 h-3 w-3" />
                    Sync
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="text-destructive"
                    onClick={() => confirm('Remove this CRM connection?') && deleteConnection(c.id)}
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
