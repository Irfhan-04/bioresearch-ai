'use client'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ResearcherIntelligence } from '@/types/researcher'

interface Props {
  intelligence?: ResearcherIntelligence | null
  generatedAt?: string | null
}

export function ResearcherIntelligenceCard({ intelligence, generatedAt }: Props) {
  if (!intelligence) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Research Intelligence</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No intelligence available yet. Run enrichment on this profile.</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Research Intelligence</CardTitle>
        {generatedAt && <p className="text-xs text-muted-foreground">Generated {new Date(generatedAt).toLocaleString()}</p>}
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-xs font-semibold uppercase text-muted-foreground">Summary</p>
          <p className="mt-1 text-sm">{intelligence.research_summary || '—'}</p>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase text-muted-foreground">Domain significance</p>
          <p className="mt-1 text-sm">{intelligence.domain_significance || '—'}</p>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase text-muted-foreground">Research connections</p>
          <p className="mt-1 text-sm">{intelligence.research_connections || '—'}</p>
        </div>

        {!!intelligence.key_topics?.length && (
          <div>
            <p className="text-xs font-semibold uppercase text-muted-foreground">Key topics</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {intelligence.key_topics.map((topic) => (
                <Badge key={topic} variant="secondary">{topic}</Badge>
              ))}
            </div>
          </div>
        )}

        {!!intelligence.research_area_tags?.length && (
          <div>
            <p className="text-xs font-semibold uppercase text-muted-foreground">Research tags</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {intelligence.research_area_tags.map((tag) => (
                <Badge key={tag} variant="outline">{tag}</Badge>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center gap-2">
          <p className="text-xs font-semibold uppercase text-muted-foreground">Activity</p>
          <Badge>{intelligence.activity_level || 'emerging'}</Badge>
        </div>

        {!!intelligence.data_gaps?.length && (
          <div>
            <p className="text-xs font-semibold uppercase text-muted-foreground">Data gaps</p>
            <ul className="mt-1 list-inside list-disc space-y-1 text-sm text-muted-foreground">
              {intelligence.data_gaps.map((gap, i) => (
                <li key={`${gap}-${i}`}>{gap}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
