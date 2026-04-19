export const APP_NAME = 'BioResearch AI'
export const APP_DESCRIPTION = 'AI-powered biotech research intelligence'

export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://bioresearch-ai-backend.onrender.com/api/v1'

export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  DASHBOARD: '/dashboard',
  RESEARCHERS: '/dashboard/researchers',
  SEARCH: '/dashboard/search',
  SCORING: '/dashboard/scoring',
  SETTINGS: '/settings',
} as const

export const RESEARCHER_STATUSES = {
  NEW: 'NEW',
  REVIEWING: 'REVIEWING',
  NOTED: 'NOTED',
  CONTACTED: 'CONTACTED',
  ARCHIVED: 'ARCHIVED',
} as const

export const SCORE_RANGES = {
  EXCELLENT: { min: 80, max: 100, label: 'Excellent' },
  GOOD: { min: 60, max: 79, label: 'Good' },
  FAIR: { min: 40, max: 59, label: 'Fair' },
  POOR: { min: 0, max: 39, label: 'Poor' },
} as const
