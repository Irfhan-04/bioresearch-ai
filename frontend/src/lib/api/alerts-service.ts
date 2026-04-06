import { apiClient } from './client'
import { API_ENDPOINTS } from './endpoints'

export const alertsService = {
  async getAlerts() {
    return (await apiClient.get(API_ENDPOINTS.ALERTS)).data
  },
  async createAlert(data: any) {
    return (await apiClient.post(API_ENDPOINTS.ALERTS, data)).data
  },
  async updateAlert(id: string, data: any) {
    return (await apiClient.patch(API_ENDPOINTS.ALERT_DETAIL(id), data)).data
  },
  async deleteAlert(id: string) {
    await apiClient.delete(API_ENDPOINTS.ALERT_DETAIL(id))
  },
  async testAlert(id: string) {
    return (await apiClient.post(API_ENDPOINTS.ALERT_TEST(id))).data
  },
}
