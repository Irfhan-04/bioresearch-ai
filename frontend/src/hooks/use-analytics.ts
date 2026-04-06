'use client'

import { useQuery } from '@tanstack/react-query'
import { analyticsService } from '@/lib/api/analytics-service'

export function useAnalytics(days = 30) {
  const daily = useQuery({
    queryKey: ['analytics', 'daily', days],
    queryFn: () => analyticsService.getDaily(days),
  })
  const topSources = useQuery({
    queryKey: ['analytics', 'top-sources', days],
    queryFn: () => analyticsService.getTopSources(days),
  })
  const engagement = useQuery({
    queryKey: ['analytics', 'engagement'],
    queryFn: analyticsService.getEngagement,
  })

  return {
    daily: daily.data,
    topSources: topSources.data,
    engagement: engagement.data,
    isLoading: daily.isLoading || topSources.isLoading,
  }
}
