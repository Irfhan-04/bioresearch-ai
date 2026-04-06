'use client'

import { useState } from 'react'
import { useLeads } from '@/hooks/use-leads'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { LeadFilters } from '@/components/leads/lead-filters'
import { ExportDialog } from '@/components/leads/export-dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { MoreHorizontal, Eye, Edit, Trash, Plus } from 'lucide-react'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import Link from 'next/link'

export default function LeadsPage() {
  const [filters, setFilters] = useState({})
  const { leads, isLoading, deleteLead } = useLeads(filters)

  const scoreBadge = (score: number | null) => {
    if (!score) return 'outline'
    if (score >= 70) return 'default'
    if (score >= 50) return 'secondary'
    return 'outline'
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Leads</h1>
          <p className="text-muted-foreground">Manage and track your biotech leads</p>
        </div>
        <div className="flex gap-2">
          <ExportDialog />
          <Link href="/dashboard/leads/new">
            <Button>
              <Plus className="mr-2 h-4 w-4" />Add Lead
            </Button>
          </Link>
        </div>
      </div>

      <LeadFilters onFiltersChange={setFilters} />

      <div className="rounded-lg border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Company</TableHead>
              <TableHead>Title</TableHead>
              <TableHead>Score</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell>
                    <Skeleton className="h-4 w-32" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-4 w-24" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-4 w-28" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-4 w-12" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-4 w-16" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-4 w-8" />
                  </TableCell>
                </TableRow>
              ))
            ) : leads.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-12 text-muted-foreground">
                  No leads found. Create your first lead!
                </TableCell>
              </TableRow>
            ) : (
              leads.map((lead) => (
                <TableRow key={lead.id}>
                  <TableCell className="font-medium">{lead.name}</TableCell>
                  <TableCell>{lead.company || '-'}</TableCell>
                  <TableCell>{lead.title || '-'}</TableCell>
                  <TableCell>
                    <Badge variant={scoreBadge(lead.propensity_score) as any}>{lead.propensity_score ?? 'N/A'}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{lead.status}</Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem asChild>
                          <Link href={`/dashboard/leads/${lead.id}`}>
                            <Eye className="mr-2 h-4 w-4" />View
                          </Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem asChild>
                          <Link href={`/dashboard/leads/${lead.id}/edit`}>
                            <Edit className="mr-2 h-4 w-4" />Edit
                          </Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={() => confirm('Delete this lead?') && deleteLead(lead.id)}
                        >
                          <Trash className="mr-2 h-4 w-4" />Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
