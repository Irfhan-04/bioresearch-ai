'use client'

import { useState } from 'react'
import { Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'

const FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'toxicology', label: 'Toxicology' },
  { value: 'drug_safety', label: 'Drug Safety' },
  { value: 'dili_hepatotoxicity', label: 'DILI' },
  { value: 'drug_discovery', label: 'Drug Discovery' },
  { value: 'organoids_3d_models', label: 'Organoids' },
  { value: 'in_vitro_models', label: 'In Vitro' },
  { value: 'preclinical', label: 'Preclinical' },
]

interface Props {
  loading?: boolean
  onSearch: (query: string, researchArea: string) => void
}

export function SemanticSearchBar({ loading = false, onSearch }: Props) {
  const [query, setQuery] = useState('')
  const [researchArea, setResearchArea] = useState('all')

  const submit = () => {
    const trimmed = query.trim()
    if (!trimmed) return
    onSearch(trimmed, researchArea)
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Ask in natural language (e.g. liver toxicity organoids)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit()}
            className="pl-8"
          />
        </div>
        <Button onClick={submit} disabled={loading || !query.trim()}>
          {loading ? 'Searching…' : 'Search'}
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((filter) => (
          <Badge
            key={filter.value}
            variant={researchArea === filter.value ? 'default' : 'outline'}
            className="cursor-pointer"
            onClick={() => setResearchArea(filter.value)}
          >
            {filter.label}
          </Badge>
        ))}
      </div>
    </div>
  )
}
