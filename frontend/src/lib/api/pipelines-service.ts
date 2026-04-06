import { apiClient } from './client'
import { API_ENDPOINTS } from './endpoints'

export const pipelinesService = {
  async getPipelines() {
    return (await apiClient.get(API_ENDPOINTS.PIPELINES)).data
  },
  async getPipeline(id: string) {
    return (await apiClient.get(API_ENDPOINTS.PIPELINE_DETAIL(id))).data
  },
  async createPipeline(data: any) {
    return (await apiClient.post(API_ENDPOINTS.PIPELINES, data)).data
  },
  async updatePipeline(id: string, data: any) {
    return (await apiClient.put(API_ENDPOINTS.PIPELINE_DETAIL(id), data)).data
  },
  async deletePipeline(id: string) {
    await apiClient.delete(API_ENDPOINTS.PIPELINE_DETAIL(id))
  },
  async runPipeline(id: string) {
    return (await apiClient.post(API_ENDPOINTS.PIPELINE_RUN(id))).data
  },
  async activatePipeline(id: string) {
    return (await apiClient.post(API_ENDPOINTS.PIPELINE_ACTIVATE(id))).data
  },
  async pausePipeline(id: string) {
    return (await apiClient.post(API_ENDPOINTS.PIPELINE_PAUSE(id))).data
  },
  async getTemplates() {
    return (await apiClient.get(API_ENDPOINTS.PIPELINE_TEMPLATES)).data
  },
  async createFromTemplate(key: string, name?: string) {
    return (await apiClient.post(API_ENDPOINTS.PIPELINE_FROM_TMPL(key), {}, { params: name ? { name } : {} })).data
  },
}
