'use client'

import { useResearcher } from '@/hooks/use-researchers'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ArrowLeft, Mail, Phone, Linkedin, Building, MapPin } from 'lucide-react'
import Link from 'next/link'
import { useParams } from 'next/navigation'

export default function ResearcherDetailPage() {
  const params = useParams()
  const { data: researcher, isLoading } = useResearcher(params.id as string)

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-6 md:grid-cols-2">{[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-48 w-full" />)}</div>
      </div>
    )
  }

  if (!researcher) return <div className="text-center py-12 text-muted-foreground">Researcher not found.</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/dashboard/researchers"><Button variant="ghost" size="icon"><ArrowLeft className="h-4 w-4" /></Button></Link>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">{researcher.name}</h1>
          <p className="text-muted-foreground">{researcher.title}</p>
        </div>
        <Badge>{researcher.status}</Badge>
        <Link href={`/dashboard/researchers/${researcher.id}/edit`}><Button>Edit Researcher</Button></Link>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Contact Information</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {researcher.email && <div className="flex items-center gap-2"><Mail className="h-4 w-4 text-muted-foreground" /><a href={`mailto:${researcher.email}`} className="text-primary hover:underline">{researcher.email}</a></div>}
            {researcher.phone && <div className="flex items-center gap-2"><Phone className="h-4 w-4 text-muted-foreground" /><a href={`tel:${researcher.phone}`}>{researcher.phone}</a></div>}
            {researcher.linkedin_url && <div className="flex items-center gap-2"><Linkedin className="h-4 w-4 text-muted-foreground" /><a href={researcher.linkedin_url} target="_blank" rel="noreferrer" className="text-primary hover:underline">LinkedIn Profile</a></div>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Organization</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {researcher.company && <div className="flex items-center gap-2"><Building className="h-4 w-4 text-muted-foreground" />{researcher.company}</div>}
            {researcher.location && <div className="flex items-center gap-2"><MapPin className="h-4 w-4 text-muted-foreground" />{researcher.location}</div>}
            {researcher.company_funding && <div><p className="text-sm text-muted-foreground">Funding</p><p className="font-medium">{researcher.company_funding}</p></div>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Researcher Intelligence</CardTitle></CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Relevance Score</p>
            <p className="text-4xl font-bold">{researcher.relevance_score ?? 'N/A'}</p>
            <Badge className="mt-2">{researcher.relevance_tier ?? 'UNSCORED'}</Badge>
            <p className="text-xs text-muted-foreground mt-2">High relevance indicates a strong match.</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Notes</CardTitle></CardHeader>
          <CardContent>
            {researcher.notes ? <p className="text-sm whitespace-pre-wrap">{researcher.notes}</p> : <p className="text-sm text-muted-foreground">No notes yet.</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
