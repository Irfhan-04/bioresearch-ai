'use client'

import { useLead } from '@/hooks/use-leads'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ArrowLeft, Mail, Phone, Linkedin, Building, MapPin } from 'lucide-react'
import Link from 'next/link'
import { useParams } from 'next/navigation'

export default function LeadDetailPage() {
  const params = useParams()
  const { data: lead, isLoading } = useLead(params.id as string)

  if (isLoading)
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-6 md:grid-cols-2">{[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-48 w-full" />)}</div>
      </div>
    )

  if (!lead) return <div className="text-center py-12 text-muted-foreground">Lead not found.</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/dashboard/leads">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">{lead.name}</h1>
          <p className="text-muted-foreground">{lead.title}</p>
        </div>
        <Badge>{lead.status}</Badge>
        <Link href={`/dashboard/leads/${lead.id}/edit`}>
          <Button>Edit Lead</Button>
        </Link>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Contact Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {lead.email && (
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <a href={`mailto:${lead.email}`} className="text-primary hover:underline">
                  {lead.email}
                </a>
              </div>
            )}
            {lead.phone && (
              <div className="flex items-center gap-2">
                <Phone className="h-4 w-4 text-muted-foreground" />
                <a href={`tel:${lead.phone}`}>{lead.phone}</a>
              </div>
            )}
            {lead.linkedin_url && (
              <div className="flex items-center gap-2">
                <Linkedin className="h-4 w-4 text-muted-foreground" />
                <a href={lead.linkedin_url} target="_blank" rel="noreferrer" className="text-primary hover:underline">
                  LinkedIn Profile
                </a>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Company</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {lead.company && (
              <div className="flex items-center gap-2">
                <Building className="h-4 w-4 text-muted-foreground" />
                {lead.company}
              </div>
            )}
            {lead.location && (
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                {lead.location}
              </div>
            )}
            {lead.company_funding && (
              <div>
                <p className="text-sm text-muted-foreground">Funding</p>
                <p className="font-medium">{lead.company_funding}</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Lead Scoring</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Propensity Score</p>
            <p className="text-4xl font-bold">{lead.propensity_score ?? 'N/A'}</p>
            <Badge className="mt-2">{lead.priority_tier}</Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Notes</CardTitle>
          </CardHeader>
          <CardContent>
            {lead.notes ? (
              <p className="text-sm whitespace-pre-wrap">{lead.notes}</p>
            ) : (
              <p className="text-sm text-muted-foreground">No notes yet.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
