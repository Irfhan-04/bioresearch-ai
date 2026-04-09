'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { SemanticSearchBar } from '@/components/charts/SemanticSearchBar'
import { researchersService, SemanticSearchResult } from '@/lib/api/researchers-service'
import { Researcher } from '@/types/researcher'

export default function SearchPage() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SemanticSearchResult | null>(null)

  const runSearch = async (query: string, researchArea: string) => {
    setLoading(true)
    try {
      const payload = await researchersService.semanticSearch({
        query,
        research_area: researchArea === 'all' ? undefined : researchArea,
        n_results: 50,
      })
      setResult(payload)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Semantic Search</h1>
        <p className="text-muted-foreground">Search indexed researchers with natural language + domain filters.</p>
      </div>

      <SemanticSearchBar loading={loading} onSearch={runSearch} />

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>
              Results for &quot;{result.query}&quot;
              <span className="ml-2 text-sm font-normal text-muted-foreground">({result.results_count} found)</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {result.researchers.length === 0 ? (
              <p className="text-sm text-muted-foreground">{result.message || 'No matches found.'}</p>
            ) : (
              <div className="space-y-3">
                {result.researchers.map((researcher: Researcher) => (
                  <div key={researcher.id} className="rounded-lg border p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <p className="font-medium">{researcher.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {researcher.title || '—'}
                          {researcher.company ? ` · ${researcher.company}` : ''}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center justify-end gap-2">
                        {typeof researcher.semantic_similarity === 'number' && (
                          <Badge variant="outline">Semantic {(researcher.semantic_similarity * 100).toFixed(1)}%</Badge>
                        )}
                        {typeof researcher.hybrid_score === 'number' && (
                          <Badge>Hybrid {(researcher.hybrid_score * 100).toFixed(1)}%</Badge>
                        )}
                        {researcher.relevance_score !== null && researcher.relevance_score !== undefined && (
                          <Badge variant="secondary">Score {researcher.relevance_score}</Badge>
                        )}
                      </div>
                    </div>
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
