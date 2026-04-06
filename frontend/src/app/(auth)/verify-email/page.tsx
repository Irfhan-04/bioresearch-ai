'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { ArrowLeft, BarChart3, Check, Loader2, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { authService } from '@/lib/api/auth-service'

type VerificationState = 'verifying' | 'success' | 'error'

export default function VerifyEmailPage() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token')?.trim() || ''
  const [state, setState] = useState<VerificationState>('verifying')
  const [message, setMessage] = useState('Verifying your email address...')

  useEffect(() => {
    let isActive = true

    const verify = async () => {
      if (!token) {
        if (isActive) {
          setState('error')
          setMessage('This verification link is missing its token.')
        }
        return
      }

      try {
        const response = await authService.verifyEmail(token)
        if (isActive) {
          setState('success')
          setMessage(response.message)
        }
      } catch (error: any) {
        if (isActive) {
          setState('error')
          setMessage(
            error.response?.data?.detail ||
              error.response?.data?.message ||
              'Could not verify your email.'
          )
        }
      }
    }

    void verify()

    return () => {
      isActive = false
    }
  }, [token])

  const isSuccess = state === 'success'

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <div className="mb-4 flex items-center justify-center gap-2">
          <BarChart3 className="h-8 w-8 text-primary" />
          <span className="text-2xl font-bold">Lead Generator</span>
        </div>
        <div className="mb-4 flex justify-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            {state === 'verifying' ? (
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            ) : isSuccess ? (
              <Check className="h-8 w-8 text-primary" />
            ) : (
              <X className="h-8 w-8 text-destructive" />
            )}
          </div>
        </div>
        <CardTitle className="text-center text-2xl">
          {state === 'verifying'
            ? 'Verifying email'
            : isSuccess
              ? 'Email verified'
              : 'Verification failed'}
        </CardTitle>
        <CardDescription className="text-center">{message}</CardDescription>
      </CardHeader>
      <CardContent />
      <CardFooter className="flex-col gap-2">
        <Link href="/login" className="w-full">
          <Button className="w-full">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to sign in
          </Button>
        </Link>
      </CardFooter>
    </Card>
  )
}
