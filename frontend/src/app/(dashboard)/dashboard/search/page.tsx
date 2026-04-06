'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Search } from 'lucide-react'
import { useLeads } from '@/hooks/use-leads'
import { Badge } from '@/components/ui/badge'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [submitted, setSubmitted] = useState('')
  const { leads, isLoading } = useLeads(submitted ? { search: submitted } : undefined)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Search</h1>
        <p className="text-muted-foreground">Search across all your leads</p>
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
              {!isLoading && <span className="ml-2 text-sm font-normal text-muted-foreground">({leads.length} found)</span>}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <p className="text-muted-foreground text-sm">Searching...</p>
            ) : leads.length === 0 ? (
              <p className="text-muted-foreground text-sm">No results found.</p>
            ) : (
              <div className="space-y-3">
                {leads.map((lead) => (
                  <div key={lead.id} className="flex items-center justify-between rounded-lg border p-3">
                    <div>
                      <p className="font-medium">{lead.name}</p>
                      <p className="text-sm text-muted-foreground">{lead.title} {lead.company && `· ${lead.company}`}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {lead.propensity_score && <Badge>{lead.propensity_score}</Badge>}
                      <Badge variant="outline">{lead.status}</Badge>
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