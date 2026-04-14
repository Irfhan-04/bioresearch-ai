import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// These routes are ALWAYS public — no login needed
const PUBLIC_ROUTES = new Set([
  '/',
  '/login',
  '/register',
  '/reset-password',
  '/verify-email',
  '/dashboard',           // guests can see the dashboard
  '/dashboard/search',    // guests can search
  '/dashboard/scoring',   // guests can see model metrics (read-only)
])

// Auth-required routes — must be logged in
const AUTH_REQUIRED_PREFIXES = [
  '/dashboard/researchers',  // managing saved researchers requires account
  '/settings',
]

export function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token')?.value
  const { pathname } = request.nextUrl

  const isPublic = PUBLIC_ROUTES.has(pathname) ||
    AUTH_REQUIRED_PREFIXES.every(prefix => !pathname.startsWith(prefix))

  // Redirect to login only for auth-required routes
  if (!isPublic && !token) {
    const url = new URL('/login', request.url)
    url.searchParams.set('from', pathname)
    return NextResponse.redirect(url)
  }

  // Already logged in — redirect away from auth pages
  if (token && (pathname === '/login' || pathname === '/register')) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
