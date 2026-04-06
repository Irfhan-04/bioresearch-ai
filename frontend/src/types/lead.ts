export interface Lead {
  id: string
  user_id: string
  name: string
  title: string | null
  company: string | null
  location: string | null
  email: string | null
  phone: string | null
  linkedin_url: string | null
  propensity_score: number | null
  rank: number | null
  priority_tier: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNSCORED'
  recent_publication: boolean
  publication_year: number | null
  publication_title: string | null
  publication_count: number
  company_funding: string | null
  company_size: string | null
  uses_3d_models: boolean
  data_sources: string[]
  tags: string[]
  notes: string | null
  status: 'NEW' | 'CONTACTED' | 'QUALIFIED' | 'PROPOSAL' | 'NEGOTIATION' | 'WON' | 'LOST'
  created_at: string
  updated_at: string
}

export interface LeadFilters {
  search?: string
  status?: string
  min_score?: number
  max_score?: number
  company?: string
  location?: string
  tags?: string[]
  page?: number
  size?: number
}

export interface CreateLeadRequest {
  name: string
  title?: string
  company?: string
  email?: string
  location?: string
}
