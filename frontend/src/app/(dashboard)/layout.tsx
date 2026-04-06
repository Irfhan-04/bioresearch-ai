import type { Metadata } from 'next'
import { Suspense } from 'react'
import { DashboardLayout } from '@/components/layout/dashboard-layout'

export const metadata: Metadata = {
  title: 'Dashboard',
  robots: { index: false, follow: false },
}

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<div />}>
      <DashboardLayout>{children}</DashboardLayout>
    </Suspense>
  )
}
