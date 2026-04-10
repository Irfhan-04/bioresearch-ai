'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ArrowLeft, Building, Mail, MapPin, Phone, Linkedin } from 'lucide-react'

import { useResearcher } from '@/hooks/use-researchers'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { ExportDialog } from '@/components/researchers/export-dialog'
import { ScoreExplanationCard } from '@/components/charts/ScoreExplanationCard'
import { ResearcherIntelligenceCard } from '@/components/charts/ResearcherIntelligenceCard'

const TIER_LABELS: Record<string, 'High' | 'Medium' | 'Low'> = { HIGH: 'High', MEDIUM: 'Medium', LOW: 'Low' }

export default function ResearcherDetailPage() {
  const params = useParams()
  const { data: researcher, isLoading } = useResearcher(params.id as string)

  if (isLoading) {
    return <div className="space-y-6"><Skeleton className="h-8 w-64" /><div className="grid gap-6 md:grid-cols-2">{[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-48 w-full" />)}</div></div>
  }

  if (!researcher) return <div className="py-12 text-center text-muted-foreground">Researcher not found.</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/dashboard/researchers"><Button variant="ghost" size="icon"><ArrowLeft className="h-4 w-4" /></Button></Link>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">{researcher.name}</h1>
          <p className="text-muted-foreground">{researcher.title || '—'}</p>
        </div>
        <Badge variant="outline">{TIER_LABELS[researcher.relevance_tier ?? ''] ?? 'Low'}</Badge>
        <ExportDialog />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Profile Signals</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between"><span className="text-muted-foreground">Relevance Score</span><span className="font-medium">{researcher.relevance_score ?? '—'}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Relevance Tier</span><span className="font-medium">{TIER_LABELS[researcher.relevance_tier ?? ''] ?? 'Low'}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Senior Researcher</span><span className="font-medium">{researcher.is_senior_researcher ? 'Yes' : 'No'}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Contact Confidence</span><span className="font-medium">{researcher.contact_confidence ?? '—'}</span></div>
            <div><p className="text-muted-foreground">Research Signals</p><p>{researcher.research_signals?.join(', ') || '—'}</p></div>
            <div><p className="text-muted-foreground">Contact Note</p><p>{researcher.notes || '—'}</p></div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Contact</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {researcher.email && <div className="flex items-center gap-2"><Mail className="h-4 w-4 text-muted-foreground" /><a href={`mailto:${researcher.email}`} className="text-primary hover:underline">{researcher.email}</a></div>}
            {researcher.phone && <div className="flex items-center gap-2"><Phone className="h-4 w-4 text-muted-foreground" /><a href={`tel:${researcher.phone}`}>{researcher.phone}</a></div>}
            {researcher.linkedin_url && <div className="flex items-center gap-2"><Linkedin className="h-4 w-4 text-muted-foreground" /><a href={researcher.linkedin_url} target="_blank" rel="noreferrer" className="text-primary hover:underline">LinkedIn Profile</a></div>}
            {researcher.company && <div className="flex items-center gap-2"><Building className="h-4 w-4 text-muted-foreground" />{researcher.company}</div>}
            {researcher.location && <div className="flex items-center gap-2"><MapPin className="h-4 w-4 text-muted-foreground" />{researcher.location}</div>}
          </CardContent>
        </Card>

        <ScoreExplanationCard relevance_score={researcher.relevance_score} relevance_tier={researcher.relevance_tier} research_area={researcher.research_area} shap_contributions={researcher.shap_contributions} />
        <ResearcherIntelligenceCard intelligence={researcher.intelligence} generatedAt={researcher.intelligence_generated_at} />
      </div>
    </div>
  )
}
