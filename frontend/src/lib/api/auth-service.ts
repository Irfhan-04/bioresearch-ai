import { apiClient } from './client'
import { API_ENDPOINTS } from './endpoints'
import { LoginRequest, LoginResponse, RegisterRequest, RegisterResponse, User } from '@/types/auth'
import { MessageResponse } from '@/types/api'

export const authService = {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const res = await apiClient.post<LoginResponse>(API_ENDPOINTS.LOGIN, credentials)
    return res.data
  },

  async register(data: RegisterRequest): Promise<RegisterResponse> {
    const res = await apiClient.post<RegisterResponse>(API_ENDPOINTS.REGISTER, data)
    return res.data
  },

  async getCurrentUser(): Promise<User> {
    const res = await apiClient.get<User>(API_ENDPOINTS.ME)
    return res.data
  },

  async logout(): Promise<void> {
    await apiClient.post(API_ENDPOINTS.LOGOUT)
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('auth-storage')
    document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'
  },

  async requestPasswordReset(email: string): Promise<MessageResponse> {
    const res = await apiClient.post<MessageResponse>(API_ENDPOINTS.FORGOT_PASSWORD, { email })
    return res.data
  },

  async resetPassword(token: string, newPassword: string): Promise<MessageResponse> {
    const res = await apiClient.post<MessageResponse>(API_ENDPOINTS.RESET_PASSWORD, {
      token,
      new_password: newPassword,
    })
    return res.data
  },

  async verifyEmail(token: string): Promise<MessageResponse> {
    const res = await apiClient.get<MessageResponse>(API_ENDPOINTS.VERIFY_EMAIL(token))
    return res.data
  },
}
