'use client'

import { Sidebar } from './sidebar'
import { Header } from './header'
import { usePathname } from 'next/navigation'

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const title = pathname.split('/').filter(Boolean).pop() || 'dashboard'

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        <Header title={title} />
        <main className="flex-1 overflow-y-auto scrollbar-thin p-6">
          {children}
        </main>
      </div>
    </div>
  )
}