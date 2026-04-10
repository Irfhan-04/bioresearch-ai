'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { SemanticSearchBar } from '@/components/charts/SemanticSearchBar'
import { researchersService, SemanticSearchResult } from '@/lib/api/researchers-service'
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

export default function SearchPage() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SemanticSearchResult | null>(null)

  const runSearch = async (query: string, researchArea: string) => {
    setLoading(true)
    try {
      const payload = await researchersService.semanticSearch({ query, research_area: researchArea === 'all' ? undefined : researchArea, n_results: 50 })
      setResult(payload)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Search</h1>
        <p className="text-muted-foreground">Semantic search across indexed researchers.</p>
      </div>

      <SemanticSearchBar loading={loading} onSearch={runSearch} />

      {result && (
        <Card>
          <CardHeader><CardTitle>Results for &quot;{result.query}&quot; <span className="ml-2 text-sm font-normal text-muted-foreground">({result.results_count} found)</span></CardTitle></CardHeader>
          <CardContent>
            {result.researchers.length === 0 ? (
              <p className="text-sm text-muted-foreground">{result.message || 'No matches found.'}</p>
            ) : (
              <div className="space-y-3">
                {result.researchers.map((researcher: Researcher) => (
                  <div key={researcher.id} className="rounded-lg border p-3">
                    <p className="font-medium">{researcher.name}</p>
                    <p className="text-sm text-muted-foreground">
                      Research Area: {researcher.research_area ? (AREA_LABELS[researcher.research_area] ?? researcher.research_area) : 'General Biotech'} · Relevance Score: {researcher.relevance_score ?? '—'} · Semantic Match: {typeof researcher.semantic_similarity === 'number' ? (researcher.semantic_similarity * 100).toFixed(1) : '—'}%
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
