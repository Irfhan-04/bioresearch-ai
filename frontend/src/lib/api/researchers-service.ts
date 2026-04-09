import { apiClient } from './client'
import { API_ENDPOINTS } from './endpoints'
import { Researcher } from '@/types/researcher'

export interface SemanticSearchParams {
  query: string
  research_area?: string
  n_results?: number
}

export interface SemanticSearchResult {
  query: string
  results_count: number
  researchers: Researcher[]
  message?: string
}

export interface ModelMetrics {
  model_type: string
  trained_at: string
  n_training_samples: number
  n_test_samples: number
  test_accuracy: number
  macro_f1: number
  per_class: Record<string, { precision: number; recall: number; f1: number }>
  confusion_matrix: number[][]
  top_10_features: Array<{ feature: string; display_name: string; importance: number }>
}

export const researchersService = {
  async semanticSearch(params: SemanticSearchParams): Promise<SemanticSearchResult> {
    const { query, research_area, n_results = 20 } = params
    const response = await apiClient.get(API_ENDPOINTS.SEARCH_SEMANTIC, {
      params: { query, research_area, n_results },
    })
    return response.data
  },

  async getModelMetrics(): Promise<ModelMetrics> {
    const response = await apiClient.get(API_ENDPOINTS.SCORING_METRICS)
    return response.data
  },
}
