'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { LayoutDashboard, Users, Search, BarChart2, LogOut, ChevronDown, Microscope, Settings } from 'lucide-react'
import { useAuth } from '@/hooks/use-auth'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'

const navLinks = [
  { href: '/dashboard', label: 'Overview', icon: LayoutDashboard },
  { href: '/dashboard/researchers', label: 'Researchers', icon: Users },
  { href: '/dashboard/search', label: 'Search', icon: Search },
  { href: '/dashboard/scoring', label: 'Model', icon: BarChart2 },
]

export function Sidebar() {
  const pathname = usePathname()
  const { logout, user } = useAuth()

  const initials = (n: string) => n.split(' ').map((x) => x[0]).join('').toUpperCase().slice(0, 2)
  const isActive = (href: string) => (href === '/dashboard' ? pathname === href : pathname === href || pathname.startsWith(`${href}/`))

  return (
    <aside className="relative flex h-full w-64 flex-col overflow-hidden border-r border-[rgba(255,255,255,0.055)] glass">
      <div className="flex h-16 items-center gap-3 border-b border-[rgba(255,255,255,0.055)] px-5">
        <div className="flex h-8 w-8 animate-pulse-glow items-center justify-center rounded-lg border border-[rgba(0,214,143,0.25)] bg-[rgba(0,214,143,0.12)]">
          <Microscope className="h-4 w-4 text-[#00d68f]" />
        </div>
        <div>
          <p className="font-syne text-sm font-700 leading-tight tracking-tight text-white">BioResearch AI</p>
          <p className="font-mono-dm text-[10px] uppercase tracking-widest text-zinc-500">Dashboard</p>
        </div>
      </div>

      <nav className="scrollbar-thin flex-1 space-y-0.5 overflow-y-auto px-3 py-4">
        {navLinks.map((item) => {
          const active = isActive(item.href)
          return (
            <Link
              key={item.label}
              href={item.href}
              className={cn(
                'group flex items-center gap-3 rounded-md border border-transparent px-3 py-2 text-sm font-medium transition-all duration-150',
                active ? 'nav-active' : 'text-zinc-500 hover:bg-white/[0.04] hover:text-zinc-200',
              )}
            >
              <item.icon className={cn('h-4 w-4 shrink-0 transition-colors', active ? 'text-[#00d68f]' : 'text-zinc-600 group-hover:text-zinc-300')} />
              <span className={active ? 'text-teal-glow' : ''}>{item.label}</span>
            </Link>
          )
        })}
      </nav>

      <div className="space-y-2 border-t border-[rgba(255,255,255,0.055)] p-3">
        {/* Guest usage indicator — only shows when not logged in */}
        {!user && (
          <div className="mx-3 mb-2 rounded-lg border border-[rgba(0,214,143,0.15)] bg-[rgba(0,214,143,0.05)] px-3 py-2.5">
            <p className="mb-1 text-[11px] font-medium uppercase tracking-widest text-[#00d68f]">
              Guest mode
            </p>
            <p className="text-[11px] text-zinc-500">
              3 searches/day
            </p>
            <Link
              href="/register"
              className="mt-1.5 block text-[11px] font-medium text-[#00d68f] hover:underline"
            >
              Sign up free for 20/day →
            </Link>
          </div>
        )}

        <Link href="/dashboard/settings" className="group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-zinc-500 transition-all duration-150 hover:bg-white/[0.04] hover:text-zinc-200">
          <Settings className="h-4 w-4 text-zinc-600 transition-colors group-hover:text-zinc-300" />
          <span>Settings</span>
        </Link>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="group flex w-full items-center gap-3 rounded-md px-2 py-2 transition-colors hover:bg-white/[0.04]">
              <Avatar className="h-8 w-8 shrink-0 ring-1 ring-[rgba(0,214,143,0.25)]">
                <AvatarFallback className="font-syne bg-[rgba(0,214,143,0.1)] text-xs font-700 text-[#00d68f]">
                  {user?.full_name ? initials(user.full_name) : 'U'}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <span className="truncate text-sm font-medium leading-tight text-zinc-200">{user?.full_name || 'User'}</span>
              </div>
              <ChevronDown className="h-3.5 w-3.5 shrink-0 text-zinc-600 transition-colors group-hover:text-zinc-400" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="glass w-48 border-[rgba(255,255,255,0.08)]">
            <DropdownMenuItem onClick={logout} className="cursor-pointer text-zinc-400 hover:text-red-400 focus:text-red-400">
              <LogOut className="mr-2 h-4 w-4" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </aside>
  )
}
