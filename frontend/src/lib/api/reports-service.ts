import { apiClient } from './client'
import { API_ENDPOINTS } from './endpoints'

export const reportsService = {
  async getFunnel(days = 90) {
    return (await apiClient.get(API_ENDPOINTS.REPORT_FUNNEL, { params: { days } })).data
  },
  async getConversion(days = 90) {
    return (await apiClient.get(API_ENDPOINTS.REPORT_CONVERSION, { params: { days } })).data
  },
  async getRoi(avgDealValue = 50000, winRatePct = 15) {
    return (await apiClient.get(API_ENDPOINTS.REPORT_ROI, { params: { avg_deal_value: avgDealValue, win_rate_pct: winRatePct } })).data
  },
  async getCohort(weeks = 8) {
    return (await apiClient.get(API_ENDPOINTS.REPORT_COHORT, { params: { weeks } })).data
  },
  async getCustom(data: { metric: string; group_by: string; days: number; filters?: any }) {
    return (await apiClient.post(API_ENDPOINTS.REPORT_CUSTOM, data)).data
  },
}
