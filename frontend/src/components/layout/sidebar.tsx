'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { LayoutDashboard, Users, Search, Settings, LogOut, ChevronDown, Target, Microscope } from 'lucide-react'
import { useAuth } from '@/hooks/use-auth'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'

const navigation = [
  { name: 'Overview', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Researchers', href: '/dashboard/researchers', icon: Users },
  { name: 'Search', href: '/dashboard/search', icon: Search },
  { name: 'Scoring', href: '/dashboard/scoring', icon: Target },
  { name: 'Settings', href: '/dashboard/settings', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  const { logout, user } = useAuth()

  const initials = (n: string) => n.split(' ').map((x) => x[0]).join('').toUpperCase().slice(0, 2)
  const isActive = (href: string) => (href === '/dashboard' ? pathname === href : pathname === href || pathname.startsWith(`${href}/`))

  return (
    <aside className="flex h-full w-64 flex-col glass border-r border-[rgba(255,255,255,0.055)] relative overflow-hidden">
      <div className="flex h-16 items-center gap-3 px-5 border-b border-[rgba(255,255,255,0.055)]">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[rgba(0,214,143,0.12)] border border-[rgba(0,214,143,0.25)] animate-pulse-glow">
          <Microscope className="h-4 w-4 text-[#00d68f]" />
        </div>
        <div>
          <p className="font-syne text-sm font-700 text-white leading-tight tracking-tight">BioResearch AI</p>
          <p className="text-[10px] text-zinc-500 font-mono-dm tracking-widest uppercase">Dashboard</p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto scrollbar-thin px-3 py-4 space-y-0.5">
        {navigation.map((item) => {
          const active = isActive(item.href)
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-all duration-150',
                active ? 'nav-active' : 'text-zinc-500 hover:text-zinc-200 hover:bg-white/[0.04] border border-transparent',
              )}
            >
              <item.icon className={cn('h-4 w-4 shrink-0 transition-colors', active ? 'text-[#00d68f]' : 'text-zinc-600 group-hover:text-zinc-300')} />
              <span className={active ? 'text-teal-glow' : ''}>{item.name}</span>
            </Link>
          )
        })}
      </nav>

      <div className="border-t border-[rgba(255,255,255,0.055)] p-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="w-full flex items-center gap-3 rounded-md px-2 py-2 hover:bg-white/[0.04] transition-colors group">
              <Avatar className="h-8 w-8 shrink-0 ring-1 ring-[rgba(0,214,143,0.25)]">
                <AvatarFallback className="bg-[rgba(0,214,143,0.1)] text-[#00d68f] text-xs font-syne font-700">
                  {user?.full_name ? initials(user.full_name) : 'U'}
                </AvatarFallback>
              </Avatar>
              <div className="flex flex-1 flex-col items-start min-w-0">
                <span className="text-sm font-medium text-zinc-200 truncate leading-tight">{user?.full_name || 'User'}</span>
              </div>
              <ChevronDown className="h-3.5 w-3.5 text-zinc-600 group-hover:text-zinc-400 transition-colors shrink-0" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48 glass border-[rgba(255,255,255,0.08)]">
            <DropdownMenuItem onClick={logout} className="text-zinc-400 hover:text-red-400 focus:text-red-400 cursor-pointer">
              <LogOut className="mr-2 h-4 w-4" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </aside>
  )
}
