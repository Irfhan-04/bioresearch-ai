'use client'

import { useState } from 'react'
import Link from 'next/link'
import { X, Zap, AlertTriangle } from 'lucide-react'

interface Props {
  searchesUsed: number
  searchesLimit: number
  isGuest: boolean
}

export function GuestBanner({ searchesUsed, searchesLimit, isGuest }: Props) {
  const [dismissed, setDismissed] = useState(false)
  if (!isGuest || dismissed) return null

  const remaining = searchesLimit - searchesUsed
  const isNearLimit = remaining <= 1
  const isAtLimit = remaining <= 0

  return (
    <div
      className={`relative flex items-center justify-between gap-4 rounded-xl border px-4 py-3 text-sm ${
        isAtLimit
          ? 'border-red-500/30 bg-red-950/30 text-red-300'
          : isNearLimit
          ? 'border-amber-500/30 bg-amber-950/20 text-amber-300'
          : 'border-[rgba(0,214,143,0.2)] bg-[rgba(0,214,143,0.05)] text-[#00d68f]'
      }`}
    >
      <div className="flex items-center gap-3">
        {isAtLimit || isNearLimit
          ? <AlertTriangle className="h-4 w-4 shrink-0" />
          : <Zap className="h-4 w-4 shrink-0" />
        }
        <span>
          {isAtLimit
            ? <>Daily guest limit reached ({searchesLimit} searches). </>
            : <>Guest mode · {remaining} search{remaining !== 1 ? 'es' : ''} remaining today. </>
          }
          <Link
            href="/register"
            className="font-semibold underline underline-offset-2 hover:no-underline"
          >
            Sign up free for 20 searches/day →
          </Link>
        </span>
      </div>
      <button
        onClick={() => setDismissed(true)}
        className="shrink-0 opacity-60 hover:opacity-100 transition-opacity"
        aria-label="Dismiss"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}
