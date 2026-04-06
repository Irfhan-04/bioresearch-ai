import { apiClient } from './client'
import { API_ENDPOINTS } from './endpoints'

export const collaborationService = {
  async getActivities(leadId: string, activityType?: string) {
    return (await apiClient.get(API_ENDPOINTS.ACTIVITIES(leadId), { params: activityType ? { activity_type: activityType } : {} })).data
  },
  async addActivity(leadId: string, data: { activity_type: string; content?: string; reminder_due_at?: string }) {
    return (await apiClient.post(API_ENDPOINTS.ACTIVITIES(leadId), data)).data
  },
  async assignLead(leadId: string, assigneeUserId: string | null) {
    return (await apiClient.post(API_ENDPOINTS.ASSIGN_LEAD(leadId), { assignee_user_id: assigneeUserId })).data
  },
  async changeStatus(leadId: string, newStatus: string) {
    return (await apiClient.post(API_ENDPOINTS.LEAD_STATUS(leadId), { new_status: newStatus })).data
  },
  async getReminders(dueWithinDays = 7) {
    return (await apiClient.get(API_ENDPOINTS.REMINDERS, { params: { due_within_days: dueWithinDays } })).data
  },
  async completeReminder(activityId: string) {
    return (await apiClient.post(API_ENDPOINTS.REMINDER_DONE(activityId))).data
  },
}
