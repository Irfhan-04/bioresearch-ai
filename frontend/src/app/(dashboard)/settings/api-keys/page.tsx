'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Copy, Eye, EyeOff, Key, Plus, Trash2 } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/use-toast'
import { apiClient } from '@/lib/api/client'

interface ApiKey {
  id: string
  name: string
  prefix: string
  created_at: string
  last_used_at: string | null
}

interface NewKeyResponse {
  id: string
  name: string
  key: string
  prefix: string
  created_at: string
}

const createSchema = z.object({
  name: z.string().min(1, 'Name is required').max(64, 'Name too long'),
})
type CreateForm = z.infer<typeof createSchema>

export default function ApiKeysPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [newKey, setNewKey] = useState<string | null>(null)
  const [showKey, setShowKey] = useState(false)

  const { data: keys = [], isLoading } = useQuery<ApiKey[]>({
    queryKey: ['api-keys'],
    queryFn: () => apiClient.get('/users/me/api-keys').then((r) => r.data),
  })

  const { register, handleSubmit, reset, formState: { errors } } = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
  })

  const createMutation = useMutation({
    mutationFn: (data: CreateForm) =>
      apiClient.post('/users/me/api-keys', data).then((r): NewKeyResponse => r.data),
    onSuccess: (data) => {
      setNewKey(data.key)
      setShowKey(false)
      reset()
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      toast({ title: 'API key created', description: 'Copy it now — it will not be shown again.' })
    },
    onError: () => {
      toast({ title: 'Failed to create key', variant: 'destructive' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (keyId: string) => apiClient.delete(`/users/me/api-keys/${keyId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      toast({ title: 'API key deleted' })
    },
    onError: () => {
      toast({ title: 'Failed to delete key', variant: 'destructive' })
    },
  })

  const copyToClipboard = async (text: string) => {
    await navigator.clipboard.writeText(text)
    toast({ title: 'Copied to clipboard' })
  }

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">API Keys</h1>
        <p className="mt-1 text-muted-foreground">
          Authenticate API requests from your own scripts and integrations.
        </p>
      </div>

      {newKey && (
        <Card className="border-green-200 bg-green-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-green-800">New key created — copy it now</CardTitle>
            <CardDescription className="text-green-700">
              This is the only time this key will be displayed.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded border bg-white px-3 py-2 text-sm font-mono text-green-900 overflow-auto">
                {showKey ? newKey : '•'.repeat(40)}
              </code>
              <Button size="icon" variant="outline" onClick={() => setShowKey((s) => !s)}>
                {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
              <Button size="icon" variant="outline" onClick={() => copyToClipboard(newKey)}>
                <Copy className="h-4 w-4" />
              </Button>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="mt-2 text-green-700"
              onClick={() => setNewKey(null)}
            >
              I have saved this key
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Create new API key</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={handleSubmit((data) => createMutation.mutate(data))}
            className="flex items-end gap-3"
          >
            <div className="flex-1 space-y-1">
              <Label htmlFor="key-name">Key name</Label>
              <Input
                id="key-name"
                placeholder="e.g. production-script"
                {...register('name')}
              />
              {errors.name && (
                <p className="text-xs text-destructive">{errors.name.message}</p>
              )}
            </div>
            <Button type="submit" disabled={createMutation.isPending}>
              <Plus className="mr-2 h-4 w-4" />
              {createMutation.isPending ? 'Creating...' : 'Create key'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Your API keys</CardTitle>
          <CardDescription>
            {isLoading ? 'Loading...' : `${keys.length} key${keys.length !== 1 ? 's' : ''}`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-14" />
              <Skeleton className="h-14" />
            </div>
          ) : keys.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-8 text-center text-muted-foreground">
              <Key className="h-8 w-8 opacity-30" />
              <p className="text-sm">No API keys yet. Create one above.</p>
            </div>
          ) : (
            <ul className="divide-y">
              {keys.map((key) => (
                <li key={key.id} className="flex items-center gap-4 py-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{key.name}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Badge variant="outline" className="font-mono text-xs">
                        {key.prefix}••••
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        Created {new Date(key.created_at).toLocaleDateString()}
                      </span>
                      {key.last_used_at && (
                        <span className="text-xs text-muted-foreground">
                          · Last used {new Date(key.last_used_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="text-destructive hover:text-destructive"
                    onClick={() => deleteMutation.mutate(key.id)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card className="border-muted">
        <CardContent className="pt-4">
          <p className="text-xs text-muted-foreground">
            Include your key as a header:{' '}
            <code className="font-mono bg-muted px-1 py-0.5 rounded">
              X-API-Key: YOUR_API_KEY
            </code>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
