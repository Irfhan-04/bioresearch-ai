import { apiClient } from './client'
import { API_ENDPOINTS } from './endpoints'
import { Researcher as Lead, ResearcherFilters as LeadFilters, CreateResearcherRequest as CreateLeadRequest } from '@/types/researcher'
import { PaginatedResponse } from '@/types/api'

export const leadsService = {
  async getLeads(filters?: LeadFilters): Promise<PaginatedResponse<Lead>> {
    const res = await apiClient.get<PaginatedResponse<Lead>>(API_ENDPOINTS.RESEARCHERS, { params: filters })
    return res.data
  },

  async getLead(id: string): Promise<Lead> {
    const res = await apiClient.get<Lead>(API_ENDPOINTS.RESEARCHER_DETAIL(id))
    return res.data
  },

  async createLead(data: CreateLeadRequest): Promise<Lead> {
    const res = await apiClient.post<Lead>(API_ENDPOINTS.RESEARCHERS, data)
    return res.data
  },

  async updateLead(id: string, data: Partial<Lead>): Promise<Lead> {
    const res = await apiClient.put<Lead>(API_ENDPOINTS.RESEARCHER_DETAIL(id), data)
    return res.data
  },

  async deleteLead(id: string): Promise<void> {
    await apiClient.delete(API_ENDPOINTS.RESEARCHER_DETAIL(id))
  },
}
