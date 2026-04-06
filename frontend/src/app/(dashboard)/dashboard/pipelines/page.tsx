'use client'

import { useState } from 'react'
import { Play, Pause, Trash, MoreHorizontal, Plus, Zap } from 'lucide-react'
import { usePipelines } from '@/hooks/use-pipelines'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'

export default function PipelinesPage() {
  const { pipelines, templates, isLoading, runPipeline, togglePipeline, deletePipeline, createFromTemplate, isRunning } =
    usePipelines()
  const [templateOpen, setTemplateOpen] = useState(false)

  const statusColor = (s: string) => {
    if (s === 'active') return 'default'
    if (s === 'running') return 'secondary'
    if (s === 'error') return 'destructive'
    return 'outline'
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Pipelines</h1>
          <p className="text-muted-foreground">Automated lead generation workflows</p>
        </div>
        <Dialog open={templateOpen} onOpenChange={setTemplateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New from Template
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Choose a Pipeline Template</DialogTitle>
            </DialogHeader>
            <div className="grid gap-3 py-2">
              {templates.map((t: any) => (
                <Card
                  key={t.key}
                  className="cursor-pointer transition-colors hover:border-primary"
                  onClick={() => {
                    createFromTemplate(t.key)
                    setTemplateOpen(false)
                  }}
                >
                  <CardHeader className="pb-1">
                    <CardTitle className="text-base">{t.name}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">{t.description}</p>
                    <div className="mt-2 flex gap-2 text-xs text-muted-foreground">
                      <span>{t.query_count} queries</span>
                      <span>·</span>
                      <span className="capitalize">{t.schedule}</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-lg" />
          ))}
        </div>
      ) : pipelines.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <Zap className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
            <p className="text-lg font-medium">No pipelines yet</p>
            <p className="mb-4 text-sm text-muted-foreground">Create one from a template to get started</p>
            <Button onClick={() => setTemplateOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Add Pipeline
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {pipelines.map((p: any) => (
            <Card key={p.id}>
              <CardContent className="flex items-center justify-between py-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{p.name}</span>
                    <Badge variant={statusColor(p.status) as any}>{p.status}</Badge>
                    <Badge variant="outline" className="capitalize">
                      {p.schedule}
                    </Badge>
                  </div>
                  <div className="flex gap-4 text-xs text-muted-foreground">
                    <span>
                      {p.run_count} runs · {p.success_count} success
                    </span>
                    <span>{p.total_leads_generated} leads generated</span>
                    {p.next_run_at && <span>Next: {new Date(p.next_run_at).toLocaleString()}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="outline" disabled={isRunning} onClick={() => runPipeline(p.id)}>
                    <Play className="mr-1 h-4 w-4" />
                    Run
                  </Button>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button size="icon" variant="ghost">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => togglePipeline(p.id, p.status !== 'active')}>
                        {p.status === 'active' ? (
                          <>
                            <Pause className="mr-2 h-4 w-4" />
                            Pause
                          </>
                        ) : (
                          <>
                            <Play className="mr-2 h-4 w-4" />
                            Activate
                          </>
                        )}
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className="text-destructive"
                        onClick={() => confirm('Delete pipeline?') && deletePipeline(p.id)}
                      >
                        <Trash className="mr-2 h-4 w-4" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
