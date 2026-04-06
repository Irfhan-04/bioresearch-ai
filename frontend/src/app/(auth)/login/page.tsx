'use client'

import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuth } from '@/hooks/use-auth'
import { Loader2, Microscope } from 'lucide-react'

const schema = z.object({
  email:    z.string().email('Invalid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
})
type Form = z.infer<typeof schema>

export default function LoginPage() {
  const { login, isLoggingIn } = useAuth()
  const { register, handleSubmit, formState: { errors } } = useForm<Form>({
    resolver: zodResolver(schema),
  })

  return (
    <div
      className="w-full max-w-sm animate-fade-up"
      style={{ animationDuration: '0.45s' }}
    >
      {/* Logo */}
      <div className="flex items-center justify-center gap-3 mb-8">
        <div
          className="flex h-10 w-10 items-center justify-center rounded-xl border border-[rgba(0,214,143,0.3)] bg-[rgba(0,214,143,0.1)]"
          style={{ boxShadow: '0 0 20px rgba(0,214,143,0.25)' }}
        >
          <Microscope className="h-5 w-5 text-[#00d68f]" />
        </div>
        <div>
          <p className="font-syne font-700 text-white text-base tracking-tight leading-tight">BioLead</p>
          <p className="font-mono-dm text-[10px] text-zinc-600 uppercase tracking-widest">Intelligence</p>
        </div>
      </div>

      {/* Card */}
      <div
        className="rounded-2xl border p-8"
        style={{
          background: 'rgba(11,18,36,0.88)',
          backdropFilter: 'blur(24px)',
          borderColor: 'rgba(0,214,143,0.12)',
          boxShadow: '0 8px 40px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.04)',
        }}
      >
        <div className="mb-6">
          <h1 className="font-syne text-2xl font-700 text-white tracking-tight">Welcome back</h1>
          <p className="text-sm text-zinc-500 mt-1">Sign in to your account</p>
        </div>

        <form onSubmit={handleSubmit((d) => login(d))} className="space-y-5">
          <div className="space-y-1.5">
            <Label htmlFor="email" className="text-xs font-medium uppercase tracking-widest text-zinc-500">
              Email
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              {...register('email')}
              className="bg-[rgba(255,255,255,0.04)] border-[rgba(255,255,255,0.08)] text-zinc-100 placeholder:text-zinc-700 focus:border-[rgba(0,214,143,0.4)] focus:ring-[rgba(0,214,143,0.2)] transition-colors"
            />
            {errors.email && <p className="text-xs text-red-400">{errors.email.message}</p>}
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label htmlFor="password" className="text-xs font-medium uppercase tracking-widest text-zinc-500">
                Password
              </Label>
              <Link href="/reset-password" className="text-xs text-[#00d68f] hover:underline">
                Forgot?
              </Link>
            </div>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              {...register('password')}
              className="bg-[rgba(255,255,255,0.04)] border-[rgba(255,255,255,0.08)] text-zinc-100 placeholder:text-zinc-700 focus:border-[rgba(0,214,143,0.4)] focus:ring-[rgba(0,214,143,0.2)] transition-colors"
            />
            {errors.password && <p className="text-xs text-red-400">{errors.password.message}</p>}
          </div>

          <button
            type="submit"
            disabled={isLoggingIn}
            className="w-full flex items-center justify-center gap-2 rounded-xl py-3 text-sm font-600 font-syne transition-all disabled:opacity-60"
            style={{
              background: isLoggingIn ? 'rgba(0,214,143,0.6)' : '#00d68f',
              color: 'hsl(222,47%,4%)',
              boxShadow: isLoggingIn ? 'none' : '0 0 24px rgba(0,214,143,0.35)',
            }}
          >
            {isLoggingIn ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Signing in…</>
            ) : (
              'Sign in'
            )}
          </button>
        </form>

        <p className="text-center text-xs text-zinc-600 mt-6">
          Don&apos;t have an account?{' '}
          <Link href="/register" className="text-[#00d68f] hover:underline font-medium">
            Create one free
          </Link>
        </p>
      </div>
    </div>
  )
}