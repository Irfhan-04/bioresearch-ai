'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { SemanticSearchBar } from '@/components/charts/SemanticSearchBar'
import { GuestBanner } from '@/components/ui/GuestBanner'
import { researchersService, SemanticSearchResult } from '@/lib/api/researchers-service'

// ... existing AREA_LABELS constant stays the same ...

export default function SearchPage() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SemanticSearchResult | null>(null)
  const [quota, setQuota] = useState<{
    is_guest: boolean
    searches_used: number
    searches_limit: number
  } | null>(null)

  const runSearch = async (query: string, researchArea: string) => {
    setLoading(true)
    try {
      const payload = await researchersService.semanticSearch({
        query,
        research_area: researchArea === 'all' ? undefined : researchArea,
        n_results: 50,
      })
      setResult(payload)
      // Extract quota from response if backend includes it
      if (payload.quota) {
        setQuota(payload.quota)
      }
    } catch (err: any) {
      // Handle daily limit exceeded (HTTP 429)
      if (err?.response?.status === 429) {
        const detail = err.response.data?.detail
        if (detail?.searches_limit) {
          setQuota({
            is_guest: detail.is_guest ?? true,
            searches_used: detail.searches_limit,
            searches_limit: detail.searches_limit,
          })
        }
      }
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

      {/* Guest usage banner */}
      {quota && (
        <GuestBanner
          searchesUsed={quota.searches_used}
          searchesLimit={quota.searches_limit}
          isGuest={quota.is_guest}
        />
      )}

      <SemanticSearchBar loading={loading} onSearch={runSearch} />

      {/* ... rest of results rendering stays the same ... */}
    </div>
  )
}
