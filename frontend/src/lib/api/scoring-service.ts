import { apiClient } from './client'
import { API_ENDPOINTS } from './endpoints'

export const scoringService = {
  async getConfig() {
    return (await apiClient.get(API_ENDPOINTS.SCORE_CONFIG)).data
  },
  async updateConfig(weights: Record<string, number>) {
    return (await apiClient.put(API_ENDPOINTS.SCORE_CONFIG, weights)).data
  },
  async getStats() {
    return (await apiClient.get(API_ENDPOINTS.SCORE_STATS)).data
  },
  async rescoreLead(id: string) {
    return (await apiClient.post(API_ENDPOINTS.SCORE_LEAD(id), {})).data
  },
  async rescoreAll() {
    return (await apiClient.post(API_ENDPOINTS.SCORE_ALL)).data
  },
}
