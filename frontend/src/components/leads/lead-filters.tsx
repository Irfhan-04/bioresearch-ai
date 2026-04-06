'use client'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Search, X } from 'lucide-react'
import { useState } from 'react'

export function LeadFilters({ onFiltersChange }: { onFiltersChange: (f: any) => void }) {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [minScore, setMinScore] = useState('')

  const apply = () =>
    onFiltersChange({
      search: search || undefined,
      status: status !== 'all' ? status : undefined,
      min_score: minScore ? parseInt(minScore) : undefined,
    })

  const reset = () => {
    setSearch('')
    setStatus('all')
    setMinScore('')
    onFiltersChange({})
  }

  return (
    <div className="flex flex-col gap-4 rounded-lg border p-4 bg-card">
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search name, company, email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>

        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="NEW">New</SelectItem>
            <SelectItem value="CONTACTED">Contacted</SelectItem>
            <SelectItem value="QUALIFIED">Qualified</SelectItem>
            <SelectItem value="WON">Won</SelectItem>
          </SelectContent>
        </Select>

        <Input
          type="number"
          placeholder="Min score"
          value={minScore}
          onChange={(e) => setMinScore(e.target.value)}
          className="w-[120px]"
          min="0"
          max="100"
        />

        <Button onClick={apply}>Apply</Button>
        <Button variant="ghost" size="icon" onClick={reset}>
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
