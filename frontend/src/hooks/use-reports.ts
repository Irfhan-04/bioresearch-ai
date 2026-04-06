'use client'

import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { reportsService } from '@/lib/api/reports-service'

export function useReports() {
  const [roiParams, setRoiParams] = useState({ avgDealValue: 50000, winRatePct: 15 })

  const funnel = useQuery({ queryKey: ['report-funnel'], queryFn: () => reportsService.getFunnel() })
  const conversion = useQuery({ queryKey: ['report-conversion'], queryFn: () => reportsService.getConversion() })
  const roi = useQuery({
    queryKey: ['report-roi', roiParams],
    queryFn: () => reportsService.getRoi(roiParams.avgDealValue, roiParams.winRatePct),
  })
  const cohort = useQuery({ queryKey: ['report-cohort'], queryFn: () => reportsService.getCohort() })

  const customMutation = useMutation({
    mutationFn: reportsService.getCustom,
  })

  return {
    funnel: funnel.data,
    conversion: conversion.data,
    roi: roi.data,
    cohort: cohort.data,
    isLoading: funnel.isLoading || conversion.isLoading,
    roiParams,
    setRoiParams,
    runCustom: (d: any) => customMutation.mutateAsync(d),
    customData: customMutation.data,
    isRunningCustom: customMutation.isPending,
  }
}
