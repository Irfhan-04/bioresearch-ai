'use client'

import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuth } from '@/hooks/use-auth'
import { Loader2, Microscope, Check, X } from 'lucide-react'
import { cn } from '@/lib/utils'

const schema = z
  .object({
    email:            z.string().email('Invalid email'),
    full_name:        z.string().min(2, 'At least 2 characters'),
    password:         z.string().min(8, 'At least 8 characters'),
    confirm_password: z.string(),
  })
  .refine((d) => d.password === d.confirm_password, {
    message: "Passwords don't match",
    path: ['confirm_password'],
  })
type RegisterForm = z.infer<typeof schema>

function PasswordStrength({ password }: { password: string }) {
  if (!password) return null
  const checks = {
    '8+ characters':     password.length >= 8,
    'Uppercase':         /[A-Z]/.test(password),
    'Lowercase':         /[a-z]/.test(password),
    'Number':            /[0-9]/.test(password),
    'Special character': /[^A-Za-z0-9]/.test(password),
  }
  const score = Object.values(checks).filter(Boolean).length
  const barColor = score >= 4 ? '#00d68f' : score >= 3 ? '#fbbf24' : '#fb7185'

  return (
    <div className="space-y-2.5 mt-2">
      {/* Bar */}
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className="h-1 flex-1 rounded-full transition-all duration-300"
            style={{
              background: score >= i ? barColor : 'rgba(255,255,255,0.07)',
              boxShadow: score >= i ? `0 0 8px ${barColor}55` : 'none',
            }}
          />
        ))}
      </div>
      {/* Checks */}
      <div className="grid grid-cols-2 gap-1">
        {Object.entries(checks).map(([label, ok]) => (
          <div key={label} className="flex items-center gap-1.5">
            {ok
              ? <Check className="h-3 w-3 text-[#00d68f] shrink-0" />
              : <X className="h-3 w-3 text-zinc-700 shrink-0" />}
            <span className={cn('text-[11px]', ok ? 'text-zinc-400' : 'text-zinc-700')}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function RegisterPage() {
  const { register: registerUser, isRegistering } = useAuth()
  const {
    register, handleSubmit, watch,
    formState: { errors },
  } = useForm<RegisterForm>({ resolver: zodResolver(schema) })
  const password = watch('password', '')

  const inputCls =
    'bg-[rgba(255,255,255,0.04)] border-[rgba(255,255,255,0.08)] text-zinc-100 placeholder:text-zinc-700 focus:border-[rgba(0,214,143,0.4)] focus:ring-[rgba(0,214,143,0.15)] transition-colors'

  return (
    <div className="w-full max-w-sm animate-fade-up" style={{ animationDuration: '0.45s' }}>
      {/* Logo */}
      <div className="flex items-center justify-center gap-3 mb-8">
        <div
          className="flex h-10 w-10 items-center justify-center rounded-xl border border-[rgba(0,214,143,0.3)] bg-[rgba(0,214,143,0.1)]"
          style={{ boxShadow: '0 0 20px rgba(0,214,143,0.22)' }}
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
          <h1 className="font-syne text-2xl font-700 text-white tracking-tight">Create account</h1>
          <p className="text-sm text-zinc-500 mt-1">Free forever up to 100 leads</p>
        </div>

        <form
          onSubmit={handleSubmit((d) =>
            registerUser({ email: d.email, password: d.password, full_name: d.full_name })
          )}
          className="space-y-4"
        >
          {/* Full name */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium uppercase tracking-widest text-zinc-500">Full name</Label>
            <Input placeholder="Jane Smith" {...register('full_name')} className={inputCls} />
            {errors.full_name && <p className="text-xs text-red-400">{errors.full_name.message}</p>}
          </div>

          {/* Email */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium uppercase tracking-widest text-zinc-500">Email</Label>
            <Input type="email" placeholder="you@example.com" {...register('email')} className={inputCls} />
            {errors.email && <p className="text-xs text-red-400">{errors.email.message}</p>}
          </div>

          {/* Password */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium uppercase tracking-widest text-zinc-500">Password</Label>
            <Input type="password" placeholder="••••••••" {...register('password')} className={inputCls} />
            <PasswordStrength password={password} />
          </div>

          {/* Confirm password */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium uppercase tracking-widest text-zinc-500">Confirm password</Label>
            <Input type="password" placeholder="••••••••" {...register('confirm_password')} className={inputCls} />
            {errors.confirm_password && (
              <p className="text-xs text-red-400">{errors.confirm_password.message}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isRegistering}
            className="w-full flex items-center justify-center gap-2 rounded-xl py-3 text-sm font-600 font-syne transition-all disabled:opacity-60 mt-2"
            style={{
              background: isRegistering ? 'rgba(0,214,143,0.6)' : '#00d68f',
              color: 'hsl(222,47%,4%)',
              boxShadow: isRegistering ? 'none' : '0 0 24px rgba(0,214,143,0.35)',
            }}
          >
            {isRegistering
              ? <><Loader2 className="h-4 w-4 animate-spin" /> Creating account…</>
              : 'Create account'}
          </button>
        </form>

        <p className="text-center text-xs text-zinc-600 mt-6">
          Already have an account?{' '}
          <Link href="/login" className="text-[#00d68f] hover:underline font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}