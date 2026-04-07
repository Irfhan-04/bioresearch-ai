export const APP_NAME = 'Biotech Lead Generator'
export const APP_DESCRIPTION = 'AI-powered lead generation for biotech companies'

export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  DASHBOARD: '/dashboard',
  LEADS: '/dashboard/researchers',
  SEARCH: '/dashboard/search',
  PIPELINES: '/dashboard/pipelines',
  ANALYTICS: '/dashboard/analytics',
  ALERTS: '/dashboard/alerts',
  REPORTS: '/dashboard/reports',
  CRM: '/dashboard/crm',
  COLLABORATION: '/dashboard/collaboration',
  SCORING: '/dashboard/scoring',
  EXPORTS: '/dashboard/exports',
  TEAMS: '/dashboard/teams',
  SETTINGS: '/settings',
} as const

export const SUBSCRIPTION_TIERS = {
  FREE: 'free',
  PRO: 'pro',
  TEAM: 'team',
  ENTERPRISE: 'enterprise',
} as const

export const LEAD_STATUSES = {
  NEW: 'NEW',
  CONTACTED: 'CONTACTED',
  QUALIFIED: 'QUALIFIED',
  PROPOSAL: 'PROPOSAL',
  NEGOTIATION: 'NEGOTIATION',
  WON: 'WON',
  LOST: 'LOST',
} as const

export const SCORE_RANGES = {
  EXCELLENT: { min: 80, max: 100, label: 'Excellent' },
  GOOD: { min: 60, max: 79, label: 'Good' },
  FAIR: { min: 40, max: 59, label: 'Fair' },
  POOR: { min: 0, max: 39, label: 'Poor' },
} as const
