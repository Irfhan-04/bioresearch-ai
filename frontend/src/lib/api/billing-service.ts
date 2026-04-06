import { apiClient } from './client'
import { API_ENDPOINTS } from './endpoints'

export interface BillingSummary {
  tier: 'free' | 'pro' | 'team' | 'enterprise'
  status: string
  monthly_limit: number
  has_active_subscription: boolean
  period_end: string | null
  days_remaining: number | null
  stripe_customer_id: string | null
  publishable_key: string
}

export const billingService = {
  getSummary: async (): Promise<BillingSummary> => {
    const res = await apiClient.get(API_ENDPOINTS.BILLING_SUMMARY)
    return res.data.data
  },

  createCheckout: async (priceId: string): Promise<string> => {
    const res = await apiClient.post(API_ENDPOINTS.BILLING_CHECKOUT, { price_id: priceId })
    return res.data.data.checkout_url
  },

  createPortal: async (): Promise<string> => {
    const res = await apiClient.post(API_ENDPOINTS.BILLING_PORTAL)
    return res.data.data.portal_url
  },

  syncSubscription: async (): Promise<BillingSummary> => {
    const res = await apiClient.post(API_ENDPOINTS.BILLING_SYNC)
    return res.data.data
  },
}
