import { ApiSuccessResponse } from '@/types/api'

export interface User {
  id: string
  email: string
  full_name: string | null
  subscription_tier: 'free' | 'pro' | 'team' | 'enterprise'
  is_active: boolean
  is_verified: boolean
  is_superuser: boolean
  created_at: string
  updated_at: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface RegisterRequest {
  email: string
  password: string
  full_name?: string
}

export type RegisterResponse = ApiSuccessResponse<{ user_id: string }>

export interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
}
