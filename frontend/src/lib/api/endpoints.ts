export const API_ENDPOINTS = {
  // Auth
  LOGIN: '/auth/login',
  REGISTER: '/auth/register',
  LOGOUT: '/auth/logout',
  REFRESH: '/auth/refresh',
  FORGOT_PASSWORD: '/auth/forgot-password',
  RESET_PASSWORD: '/auth/reset-password',
  VERIFY_EMAIL: (token: string) => `/auth/verify-email/${token}`,

  // Users
  ME: '/users/me',
  CHANGE_PASSWORD: '/users/me/password',
  API_KEYS: '/users/me/api-keys',
  PREFERENCES: '/users/me/preferences',

  // Researchers
  RESEARCHERS: '/researchers',
  RESEARCHER_DETAIL: (id: string) => `/researchers/${id}`,
  RESEARCHER_BULK_DELETE: '/researchers/bulk/delete',
  RESEARCHER_BULK_CREATE: '/researchers/bulk/create',

  // Search
  SEARCH: '/search',
  SEARCH_SEMANTIC: '/search/semantic',
  SEARCH_HISTORY: '/search/history',
  SEARCH_STATUS: '/search/status/quality',

  // Export
  EXPORT: '/export',
  EXPORT_DETAIL: (id: string) => `/export/${id}`,

  // Enrichment
  ENRICH_RESEARCHER: (id: string) => `/enrich/researchers/${id}`,

  // Scoring
  SCORE_RESEARCHER: (id: string) => `/scoring/researchers/${id}/recalculate`,
  SCORE_BULK: '/scoring/researchers/bulk/recalculate',
  SCORE_ALL: '/scoring/researchers/all/recalculate',
  SCORE_CONFIG: '/scoring/config',
  SCORE_STATS: '/scoring/stats',
  SCORING_METRICS: '/scoring/metrics',

  // Legacy dashboard stats
  STATS: '/dashboard/stats',
} as const
