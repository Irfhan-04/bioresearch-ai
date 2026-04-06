import { Suspense } from 'react'

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-10">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(circle at top left, rgba(0,214,143,0.14), transparent 32%), radial-gradient(circle at bottom right, rgba(167,139,250,0.12), transparent 30%)',
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-px"
        style={{ background: 'linear-gradient(90deg, transparent, rgba(0,214,143,0.4), transparent)' }}
      />
      <div className="relative z-10 flex w-full justify-center">
        <Suspense fallback={<div />}>{children}</Suspense>
      </div>
    </div>
  )
}
