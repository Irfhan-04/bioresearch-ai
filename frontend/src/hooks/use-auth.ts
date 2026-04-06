'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { authService } from '@/lib/api/auth-service'
import { useAuthStore } from '@/stores/auth-store'
import { LoginRequest, RegisterRequest } from '@/types/auth'
import { useToast } from '@/components/ui/use-toast'

const persistSession = (accessToken: string, refreshToken: string) => {
  localStorage.setItem('access_token', accessToken)
  localStorage.setItem('refresh_token', refreshToken)
  document.cookie = `access_token=${accessToken}; path=/; max-age=${60 * 60 * 24 * 7}`
}

const clearSession = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('auth-storage')
  document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'
}

export function useAuth() {
  const router = useRouter()
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const { user, isAuthenticated, setUser, setAuthenticated, logout: storeLogout } = useAuthStore()

  const { data: currentUser, isLoading } = useQuery({
    queryKey: ['user', 'me'],
    queryFn: authService.getCurrentUser,
    enabled: isAuthenticated,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  const loginMutation = useMutation({
    mutationFn: async (credentials: LoginRequest) => {
      const session = await authService.login(credentials)
      persistSession(session.access_token, session.refresh_token)
      const currentUser = await authService.getCurrentUser()
      return { session, currentUser }
    },
    onSuccess: ({ currentUser }) => {
      setUser(currentUser)
      setAuthenticated(true)
      toast({ title: 'Success', description: 'Logged in successfully' })
      router.push('/dashboard')
    },
    onError: (error: any) => {
      clearSession()
      setUser(null)
      setAuthenticated(false)
      toast({
        title: 'Error',
        description: error.response?.data?.detail || error.response?.data?.message || 'Login failed',
        variant: 'destructive',
      })
    },
  })

  const registerMutation = useMutation({
    mutationFn: authService.register,
    onSuccess: (data) => {
      toast({
        title: 'Success',
        description: data.message || 'Account created. Please log in.',
      })
      router.push('/login')
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description:
          error.response?.data?.detail || error.response?.data?.message || 'Registration failed',
        variant: 'destructive',
      })
    },
  })

  const logoutMutation = useMutation({
    mutationFn: authService.logout,
    onSuccess: () => {
      storeLogout()
      queryClient.clear()
      router.push('/login')
    },
  })

  return {
    user: currentUser || user,
    isAuthenticated,
    isLoading,
    login: (c: LoginRequest) => loginMutation.mutate(c),
    register: (d: RegisterRequest) => registerMutation.mutate(d),
    logout: () => logoutMutation.mutate(),
    isLoggingIn: loginMutation.isPending,
    isRegistering: registerMutation.isPending,
  }
}
