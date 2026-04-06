import { apiClient } from './client'
import { API_ENDPOINTS } from './endpoints'

export const analyticsService = {
  async getDaily(days = 30) {
    return (await apiClient.get(API_ENDPOINTS.ANALYTICS_DAILY, { params: { days } })).data
  },
  async getTopSources(days = 30) {
    return (await apiClient.get(API_ENDPOINTS.ANALYTICS_TOP_SOURCES, { params: { days } })).data
  },
  async getExports(days = 30) {
    return (await apiClient.get(API_ENDPOINTS.ANALYTICS_EXPORTS, { params: { days } })).data
  },
  async getEngagement() {
    return (await apiClient.get(API_ENDPOINTS.ANALYTICS_ENGAGEMENT)).data
  },
}
