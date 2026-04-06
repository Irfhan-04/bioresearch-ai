import { apiClient } from './client'
import { API_ENDPOINTS } from './endpoints'

export const crmService = {
  async getConnections() {
    return (await apiClient.get(API_ENDPOINTS.CRM)).data
  },
  async createConnection(data: any) {
    return (await apiClient.post(API_ENDPOINTS.CRM, data)).data
  },
  async updateConnection(id: string, data: any) {
    return (await apiClient.patch(API_ENDPOINTS.CRM_DETAIL(id), data)).data
  },
  async deleteConnection(id: string) {
    await apiClient.delete(API_ENDPOINTS.CRM_DETAIL(id))
  },
  async testConnection(id: string) {
    return (await apiClient.post(API_ENDPOINTS.CRM_TEST(id))).data
  },
  async syncLeads(id: string, data?: { lead_ids?: string[]; dry_run?: boolean }) {
    return (await apiClient.post(API_ENDPOINTS.CRM_SYNC(id), data || {})).data
  },
  async getLogs(id: string) {
    return (await apiClient.get(API_ENDPOINTS.CRM_LOGS(id))).data
  },
}
