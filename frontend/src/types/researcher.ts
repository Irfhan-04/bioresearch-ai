export interface SHAPContribution {
  feature: string
  display_name: string
  shap_value: number
  direction: 'positive' | 'negative'
}

export interface ResearcherIntelligence {
  research_summary: string
  domain_significance: string
  research_connections: string
  key_topics: string[]
  research_area_tags: string[]
  activity_level: 'highly_active' | 'moderately_active' | 'emerging'
  data_gaps: string[]
}

export interface Researcher {
  id: string
  user_id: string
  name: string
  title: string | null
  company: string | null
  location: string | null
  email: string | null
  phone: string | null
  linkedin_url: string | null
  relevance_score: number | null
  rank: number | null
  relevance_tier: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNSCORED'
  recent_publication: boolean
  publication_year: number | null
  publication_title: string | null
  publication_count: number
  company_funding: string | null
  company_size: string | null
  uses_3d_models: boolean
  data_sources: string[]
  tags: string[]
  research_signals?: string[]
  is_senior_researcher?: boolean
  contact_confidence?: number
  notes: string | null
  status: string
  created_at: string
  updated_at: string

  // AI/ML fields
  abstract_text?: string | null
  abstract_embedding_id?: string | null
  abstract_relevance_score?: number | null
  research_area?: string | null
  domain_coverage_score?: number | null
  relevance_confidence?: number | null
  shap_contributions?: SHAPContribution[] | null
  intelligence?: ResearcherIntelligence | null
  intelligence_generated_at?: string | null

  // Search result fields
  semantic_similarity?: number | null
  hybrid_score?: number | null
}

export interface ResearcherFilters {
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

export interface CreateResearcherRequest {
  name: string
  title?: string
  company?: string
  email?: string
  location?: string
}
