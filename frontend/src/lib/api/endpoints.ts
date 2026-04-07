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

  LEADS: '/researchers',
  LEAD_DETAIL: (id: string) => `/researchers/${id}`,

  // Search
  SEARCH: '/search',
  SEARCH_HISTORY: '/search/history',
  SEARCH_STATUS: '/search/status/quality',

  // Export
  EXPORT: '/export',
  EXPORT_DETAIL: (id: string) => `/export/${id}`,

  // Enrichment
  ENRICH_LEAD: (id: string) => `/enrich/leads/${id}`,

  // Scoring
  SCORE_LEAD: (id: string) => `/scoring/leads/${id}/recalculate`,
  SCORE_BULK: '/scoring/leads/bulk/recalculate',
  SCORE_ALL: '/scoring/leads/all/recalculate',
  SCORE_CONFIG: '/scoring/config',
  SCORE_STATS: '/scoring/stats',

  // Pipelines
  PIPELINES: '/pipelines',
  PIPELINE_DETAIL: (id: string) => `/pipelines/${id}`,
  PIPELINE_RUN: (id: string) => `/pipelines/${id}/run`,
  PIPELINE_ACTIVATE: (id: string) => `/pipelines/${id}/activate`,
  PIPELINE_PAUSE: (id: string) => `/pipelines/${id}/pause`,
  PIPELINE_HISTORY: (id: string) => `/pipelines/${id}/history`,
  PIPELINE_STATS: (id: string) => `/pipelines/${id}/stats`,
  PIPELINE_TEMPLATES: '/pipelines/templates',
  PIPELINE_FROM_TMPL: (key: string) => `/pipelines/templates/${key}/apply`,

  // Analytics
  ANALYTICS_DAILY: '/analytics/me/daily',
  ANALYTICS_TOP_SOURCES: '/analytics/me/top-sources',
  ANALYTICS_EXPORTS: '/analytics/me/exports',
  ANALYTICS_ENGAGEMENT: '/analytics/me/engagement',
  ANALYTICS_ADMIN: '/analytics/admin/overview',
  ANALYTICS_REVENUE_SUMMARY: '/analytics/revenue/summary',

  // Billing
  BILLING_SUMMARY: '/billing/summary',
  BILLING_CHECKOUT: '/billing/checkout',
  BILLING_PORTAL: '/billing/portal',
  BILLING_SYNC: '/billing/sync',

  // Alerts
  ALERTS: '/alerts',
  ALERT_DETAIL: (id: string) => `/alerts/${id}`,
  ALERT_TEST: (id: string) => `/alerts/${id}/test`,

  // Teams
  TEAMS: '/teams',
  TEAM_DETAIL: (id: string) => `/teams/${id}`,
  TEAM_MEMBERS: (id: string) => `/teams/${id}/members`,
  TEAM_MEMBER_ROLE: (tid: string, uid: string) => `/teams/${tid}/members/${uid}/role`,
  TEAM_MEMBER_REMOVE: (tid: string, uid: string) => `/teams/${tid}/members/${uid}`,
  TEAM_INVITATIONS: (id: string) => `/teams/${id}/invitations`,
  TEAM_INVITE_ACCEPT: (token: string) => `/teams/invitations/accept/${token}`,
  TEAM_TRANSFER_OWNERSHIP: (id: string) => `/teams/${id}/transfer-ownership`,

  // CRM
  CRM: '/crm',
  CRM_DETAIL: (id: string) => `/crm/${id}`,
  CRM_TEST: (id: string) => `/crm/${id}/test`,
  CRM_SYNC: (id: string) => `/crm/${id}/sync`,
  CRM_LOGS: (id: string) => `/crm/${id}/logs`,

  // Collaboration
  ACTIVITIES: (leadId: string) => `/collaboration/leads/${leadId}/activities`,
  ASSIGN_LEAD: (leadId: string) => `/collaboration/leads/${leadId}/assign`,
  LEAD_STATUS: (leadId: string) => `/collaboration/leads/${leadId}/status`,
  REMINDERS: '/collaboration/reminders',
  REMINDER_DONE: (id: string) => `/collaboration/reminders/${id}/done`,

  // Reports
  REPORT_FUNNEL: '/reports/funnel',
  REPORT_CONVERSION: '/reports/conversion',
  REPORT_ROI: '/reports/roi',
  REPORT_COHORT: '/reports/cohort',
  REPORT_CUSTOM: '/reports/custom',

  // Webhooks
  WEBHOOKS: '/webhooks',
  WEBHOOK_DETAIL: (id: string) => `/webhooks/${id}`,
  WEBHOOK_TEST: (id: string) => `/webhooks/${id}/test`,

  // Admin
  ADMIN_USERS: '/admin/users',
  ADMIN_FLAGS: '/admin/flags',
  ADMIN_TICKETS: '/admin/tickets',
  ADMIN_HEALTH: '/admin/health/system',

  // Legacy dashboard stats
  STATS: '/dashboard/stats',
} as const
