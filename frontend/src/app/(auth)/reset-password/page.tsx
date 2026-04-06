'use client'

export const dynamic = 'force-dynamic'

import { useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ArrowLeft, Loader2, Microscope, Check, MailCheck } from 'lucide-react'
import { authService } from '@/lib/api/auth-service'
import { useToast } from '@/components/ui/use-toast'

const requestSchema = z.object({ email: z.string().email('Invalid email') })
const confirmSchema = z
  .object({
    new_password:     z.string().min(8, 'At least 8 characters'),
    confirm_password: z.string(),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: "Passwords don't match",
    path: ['confirm_password'],
  })

type RequestForm = z.infer<typeof requestSchema>
type ConfirmForm = z.infer<typeof confirmSchema>

const inputCls =
  'bg-[rgba(255,255,255,0.04)] border-[rgba(255,255,255,0.08)] text-zinc-100 placeholder:text-zinc-700 focus:border-[rgba(0,214,143,0.4)] focus:ring-[rgba(0,214,143,0.15)] transition-colors'

const cardStyle = {
  background: 'rgba(11,18,36,0.88)',
  backdropFilter: 'blur(24px)',
  borderColor: 'rgba(0,214,143,0.12)',
  boxShadow: '0 8px 40px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.04)',
}

function Logo() {
  return (
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
  )
}

export default function ResetPasswordPage() {
  const searchParams  = useSearchParams()
  const token         = searchParams.get('token')?.trim() || ''
  const isConfirmFlow = token.length > 0
  const [isLoading, setIsLoading] = useState(false)
  const [success, setSuccess]     = useState(false)
  const { toast } = useToast()

  const requestForm = useForm<RequestForm>({ resolver: zodResolver(requestSchema) })
  const confirmForm = useForm<ConfirmForm>({ resolver: zodResolver(confirmSchema) })

  const onRequest = async (d: RequestForm) => {
    setIsLoading(true)
    try {
      await authService.requestPasswordReset(d.email)
      setSuccess(true)
    } catch (e: any) {
      toast({
        title: 'Error',
        description: e.response?.data?.detail || 'Failed to send email',
        variant: 'destructive',
      })
    } finally { setIsLoading(false) }
  }

  const onConfirm = async (d: ConfirmForm) => {
    setIsLoading(true)
    try {
      await authService.resetPassword(token, d.new_password)
      setSuccess(true)
    } catch (e: any) {
      toast({
        title: 'Error',
        description: e.response?.data?.detail || 'Failed to reset password',
        variant: 'destructive',
      })
    } finally { setIsLoading(false) }
  }

  /* ── Success state ── */
  if (success) {
    return (
      <div className="w-full max-w-sm animate-fade-up">
        <Logo />
        <div className="rounded-2xl border p-8 text-center" style={cardStyle}>
          {/* Icon */}
          <div
            className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full"
            style={{
              background: 'rgba(0,214,143,0.1)',
              border: '1px solid rgba(0,214,143,0.25)',
              boxShadow: '0 0 24px rgba(0,214,143,0.25)',
            }}
          >
            {isConfirmFlow
              ? <Check className="h-7 w-7 text-[#00d68f]" />
              : <MailCheck className="h-7 w-7 text-[#00d68f]" />}
          </div>
          <h2 className="font-syne text-xl font-700 text-white mb-2">
            {isConfirmFlow ? 'Password updated' : 'Check your inbox'}
          </h2>
          <p className="text-sm text-zinc-500 mb-6">
            {isConfirmFlow
              ? 'Your password has been reset. You can sign in now.'
              : `We sent instructions to ${requestForm.getValues('email')}`}
          </p>
          <Link
            href="/login"
            className="inline-flex items-center gap-2 rounded-xl px-6 py-2.5 text-sm font-600 font-syne transition-all"
            style={{ background: '#00d68f', color: 'hsl(222,47%,4%)', boxShadow: '0 0 20px rgba(0,214,143,0.3)' }}
          >
            <ArrowLeft className="h-4 w-4" /> Back to sign in
          </Link>
          {!isConfirmFlow && (
            <button
              onClick={() => setSuccess(false)}
              className="mt-3 block w-full text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
            >
              Try a different email
            </button>
          )}
        </div>
      </div>
    )
  }

  /* ── Main form ── */
  return (
    <div className="w-full max-w-sm animate-fade-up" style={{ animationDuration: '0.45s' }}>
      <Logo />
      <div className="rounded-2xl border p-8" style={cardStyle}>
        <div className="mb-6">
          <h1 className="font-syne text-2xl font-700 text-white tracking-tight">
            {isConfirmFlow ? 'Set new password' : 'Reset password'}
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            {isConfirmFlow
              ? 'Choose a strong new password'
              : "Enter your email and we'll send instructions"}
          </p>
        </div>

        {isConfirmFlow ? (
          <form onSubmit={confirmForm.handleSubmit(onConfirm)} className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium uppercase tracking-widest text-zinc-500">New password</Label>
              <Input type="password" placeholder="Create a strong password" {...confirmForm.register('new_password')} className={inputCls} />
              {confirmForm.formState.errors.new_password && (
                <p className="text-xs text-red-400">{confirmForm.formState.errors.new_password.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium uppercase tracking-widest text-zinc-500">Confirm password</Label>
              <Input type="password" placeholder="Repeat your password" {...confirmForm.register('confirm_password')} className={inputCls} />
              {confirmForm.formState.errors.confirm_password && (
                <p className="text-xs text-red-400">{confirmForm.formState.errors.confirm_password.message}</p>
              )}
            </div>
            <SubmitBtn loading={isLoading} label="Update password" />
          </form>
        ) : (
          <form onSubmit={requestForm.handleSubmit(onRequest)} className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium uppercase tracking-widest text-zinc-500">Email</Label>
              <Input type="email" placeholder="you@example.com" {...requestForm.register('email')} className={inputCls} />
              {requestForm.formState.errors.email && (
                <p className="text-xs text-red-400">{requestForm.formState.errors.email.message}</p>
              )}
            </div>
            <SubmitBtn loading={isLoading} label="Send instructions" />
          </form>
        )}

        <Link
          href="/login"
          className="mt-5 flex items-center justify-center gap-1.5 text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to sign in
        </Link>
      </div>
    </div>
  )
}

function SubmitBtn({ loading, label }: { loading: boolean; label: string }) {
  return (
    <button
      type="submit"
      disabled={loading}
      className="w-full flex items-center justify-center gap-2 rounded-xl py-3 text-sm font-600 font-syne transition-all disabled:opacity-60 mt-1"
      style={{
        background: loading ? 'rgba(0,214,143,0.6)' : '#00d68f',
        color: 'hsl(222,47%,4%)',
        boxShadow: loading ? 'none' : '0 0 24px rgba(0,214,143,0.35)',
      }}
    >
      {loading ? <><Loader2 className="h-4 w-4 animate-spin" /> Sending…</> : label}
    </button>
  )
}