import { apiClient } from './client'
import { API_ENDPOINTS } from './endpoints'

export const teamsService = {
  async getTeams() {
    return (await apiClient.get(API_ENDPOINTS.TEAMS)).data
  },
  async createTeam(data: { name: string; description?: string }) {
    return (await apiClient.post(API_ENDPOINTS.TEAMS, data)).data
  },
  async getTeam(id: string) {
    return (await apiClient.get(API_ENDPOINTS.TEAM_DETAIL(id))).data
  },
  async updateTeam(id: string, data: any) {
    return (await apiClient.put(API_ENDPOINTS.TEAM_DETAIL(id), data)).data
  },
  async deleteTeam(id: string) {
    await apiClient.delete(API_ENDPOINTS.TEAM_DETAIL(id))
  },
  async getMembers(id: string) {
    return (await apiClient.get(API_ENDPOINTS.TEAM_MEMBERS(id))).data
  },
  async updateMemberRole(teamId: string, userId: string, role: string) {
    return (await apiClient.patch(API_ENDPOINTS.TEAM_MEMBER_ROLE(teamId, userId), { role })).data
  },
  async removeMember(teamId: string, userId: string) {
    await apiClient.delete(API_ENDPOINTS.TEAM_MEMBER_REMOVE(teamId, userId))
  },
  async inviteMember(teamId: string, data: { email: string; role: string }) {
    return (await apiClient.post(API_ENDPOINTS.TEAM_INVITATIONS(teamId), data)).data
  },
  async acceptInvitation(token: string) {
    return (await apiClient.get(API_ENDPOINTS.TEAM_INVITE_ACCEPT(token))).data
  },
}
