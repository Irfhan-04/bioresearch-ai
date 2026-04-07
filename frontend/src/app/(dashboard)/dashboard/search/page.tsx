'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Search } from 'lucide-react'
import { useResearchers } from '@/hooks/use-researchers'
import { Badge } from '@/components/ui/badge'
import { Researcher } from '@/types/researcher'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [submitted, setSubmitted] = useState('')
  const { researchers, isLoading } = useResearchers(submitted ? { search: submitted } : undefined)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Search</h1>
        <p className="text-muted-foreground">Search across all your researchers</p>
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by name, company, title, email..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && setSubmitted(query)}
            className="pl-8"
          />
        </div>
        <Button onClick={() => setSubmitted(query)}>Search</Button>
      </div>

      {submitted && (
        <Card>
          <CardHeader>
            <CardTitle>
              Results for &quot;{submitted}&quot;
              {!isLoading && <span className="ml-2 text-sm font-normal text-muted-foreground">({researchers.length} found)</span>}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <p className="text-muted-foreground text-sm">Searching...</p>
            ) : researchers.length === 0 ? (
              <p className="text-muted-foreground text-sm">No results found.</p>
            ) : (
              <div className="space-y-3">
                {researchers.map((researcher: Researcher) => (
                  <div key={researcher.id} className="flex items-center justify-between rounded-lg border p-3">
                    <div>
                      <p className="font-medium">{researcher.name}</p>
                      <p className="text-sm text-muted-foreground">{researcher.title} {researcher.company && `· ${researcher.company}`}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {researcher.relevance_score && <Badge>{researcher.relevance_score}</Badge>}
                      <Badge variant="outline">{researcher.status}</Badge>
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