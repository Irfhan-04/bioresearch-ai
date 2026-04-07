'use client'

import { useState } from 'react'
import { useResearchers } from '@/hooks/use-researchers'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { ResearcherFilters } from '@/components/researchers/researcher-filters'
import { ExportDialog } from '@/components/researchers/export-dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { MoreHorizontal, Eye, Edit, Trash, Plus } from 'lucide-react'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import Link from 'next/link'
import { Researcher } from '@/types/researcher'

export default function ResearchersPage() {
  const [filters, setFilters] = useState({})
  const { researchers, isLoading, deleteResearcher } = useResearchers(filters)

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
          <h1 className="text-3xl font-bold">Researchers</h1>
          <p className="text-muted-foreground">Manage and track your indexed researchers</p>
        </div>
        <div className="flex gap-2">
          <ExportDialog />
          <Link href="/dashboard/researchers/new">
            <Button>
              <Plus className="mr-2 h-4 w-4" />Add Researcher
            </Button>
          </Link>
        </div>
      </div>

      <ResearcherFilters onFiltersChange={setFilters} />

      <div className="rounded-lg border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Researcher</TableHead>
              <TableHead>Company</TableHead>
              <TableHead>Title</TableHead>
              <TableHead>Relevance Score</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-28" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-8" /></TableCell>
                </TableRow>
              ))
            ) : researchers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-12 text-muted-foreground">
                  No researchers found. Add your first researcher!
                </TableCell>
              </TableRow>
            ) : (
              researchers.map((researcher: Researcher) => (
                <TableRow key={researcher.id}>
                  <TableCell className="font-medium">{researcher.name}</TableCell>
                  <TableCell>{researcher.company || '-'}</TableCell>
                  <TableCell>{researcher.title || '-'}</TableCell>
                  <TableCell>
                    <Badge variant={scoreBadge(researcher.relevance_score) as any}>{researcher.relevance_score ?? 'N/A'}</Badge>
                  </TableCell>
                  <TableCell><Badge variant="outline">{researcher.status}</Badge></TableCell>
                  <TableCell className="text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon"><MoreHorizontal className="h-4 w-4" /></Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem asChild>
                          <Link href={`/dashboard/researchers/${researcher.id}`}><Eye className="mr-2 h-4 w-4" />View</Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem asChild>
                          <Link href={`/dashboard/researchers/${researcher.id}/edit`}><Edit className="mr-2 h-4 w-4" />Edit</Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem className="text-destructive" onClick={() => confirm('Delete this researcher?') && deleteResearcher(researcher.id)}>
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
