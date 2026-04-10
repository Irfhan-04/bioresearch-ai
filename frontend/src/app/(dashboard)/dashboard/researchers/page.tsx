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

const AREA_LABELS: Record<string, string> = {
  toxicology: 'Toxicology',
  drug_safety: 'Drug Safety',
  drug_discovery: 'Drug Discovery',
  organoids: 'Organoids',
  in_vitro: 'In Vitro',
  biomarkers: 'Biomarkers',
  preclinical: 'Preclinical',
  general_biotech: 'General Biotech',
}

const TIER_LABELS: Record<string, 'High' | 'Medium' | 'Low'> = {
  HIGH: 'High',
  MEDIUM: 'Medium',
  LOW: 'Low',
}

export default function ResearchersPage() {
  const [filters, setFilters] = useState({})
  const { researchers, isLoading, deleteResearcher } = useResearchers(filters)

  const activityLevel = (researcher: Researcher) => researcher.intelligence?.activity_level?.replaceAll('_', ' ') ?? '—'

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Researchers</h1>
          <p className="text-muted-foreground">Manage and track your indexed researchers.</p>
        </div>
        <div className="flex gap-2">
          <ExportDialog />
          <Link href="/dashboard/researchers/new">
            <Button><Plus className="mr-2 h-4 w-4" />Add Researcher</Button>
          </Link>
        </div>
      </div>

      <ResearcherFilters onFiltersChange={setFilters} />

      <div className="rounded-lg border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Researcher</TableHead>
              <TableHead>Relevance Score</TableHead>
              <TableHead>Research Area</TableHead>
              <TableHead>Tier</TableHead>
              <TableHead>Activity Level</TableHead>
              <TableHead>Contact</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-8" /></TableCell>
                </TableRow>
              ))
            ) : researchers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-12 text-center text-muted-foreground">No researchers found.</TableCell>
              </TableRow>
            ) : (
              researchers.map((researcher: Researcher) => (
                <TableRow key={researcher.id}>
                  <TableCell className="font-medium">{researcher.name}</TableCell>
                  <TableCell>{researcher.relevance_score ?? 'N/A'}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{researcher.research_area ? (AREA_LABELS[researcher.research_area] ?? researcher.research_area) : 'General Biotech'}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">{TIER_LABELS[researcher.relevance_tier ?? ''] ?? 'Low'}</Badge>
                  </TableCell>
                  <TableCell className="capitalize">{activityLevel(researcher)}</TableCell>
                  <TableCell>{researcher.email || researcher.linkedin_url || '—'}</TableCell>
                  <TableCell className="text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon"><MoreHorizontal className="h-4 w-4" /></Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem asChild><Link href={`/dashboard/researchers/${researcher.id}`}><Eye className="mr-2 h-4 w-4" />View</Link></DropdownMenuItem>
                        <DropdownMenuItem asChild><Link href={`/dashboard/researchers/${researcher.id}/edit`}><Edit className="mr-2 h-4 w-4" />Edit</Link></DropdownMenuItem>
                        <DropdownMenuItem className="text-destructive" onClick={() => confirm('Delete this researcher?') && deleteResearcher(researcher.id)}><Trash className="mr-2 h-4 w-4" />Delete</DropdownMenuItem>
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
