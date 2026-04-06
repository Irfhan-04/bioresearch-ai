'use client'

import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { AlertCircle, Check, Users, Zap } from 'lucide-react'
import { useSearchParams } from 'next/navigation'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/use-toast'
import { BillingSummary, billingService } from '@/lib/api/billing-service'

const TIERS = [
  {
    id: 'free',
    name: 'Free',
    price: '$0',
    period: '/month',
    description: 'Get started with lead generation',
    icon: Zap,
    color: 'text-gray-600',
    popular: false,
    priceId: null,
    features: [
      '100 leads / month',
      '1 data source (PubMed)',
      'Basic scoring algorithm',
      'CSV export',
      'Community support',
    ],
  },
  {
    id: 'pro',
    name: 'Pro',
    price: '$49',
    period: '/month',
    description: 'For individual business developers',
    icon: Zap,
    color: 'text-blue-600',
    priceId: process.env.NEXT_PUBLIC_STRIPE_PRO_PRICE_ID ?? null,
    popular: true,
    features: [
      '1,000 leads / month',
      '5 data sources',
      'AI-powered scoring',
      'All export formats',
      'API access',
      'Email support',
    ],
  },
  {
    id: 'team',
    name: 'Team',
    price: '$199',
    period: '/month',
    description: 'For BD teams with collaboration needs',
    icon: Users,
    color: 'text-purple-600',
    popular: false,
    priceId: process.env.NEXT_PUBLIC_STRIPE_TEAM_PRICE_ID ?? null,
    features: [
      '5,000 leads / month',
      'Unlimited data sources',
      'Team collaboration',
      'CRM integrations',
      'Advanced analytics',
      'Priority support',
    ],
  },
] as const

function UsageMeter({ summary }: { summary: BillingSummary }) {
  const limitLabel =
    summary.monthly_limit >= 999999 ? 'Unlimited' : summary.monthly_limit.toLocaleString()

  const statusColor: Record<string, string> = {
    active: 'bg-green-100 text-green-800',
    trialing: 'bg-blue-100 text-blue-800',
    past_due: 'bg-red-100 text-red-800',
    canceled: 'bg-gray-100 text-gray-600',
    free: 'bg-gray-100 text-gray-600',
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Current plan</CardTitle>
          <Badge className={statusColor[summary.status] ?? 'bg-gray-100 text-gray-600'}>
            {summary.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-semibold capitalize">{summary.tier}</span>
          {summary.tier !== 'free' && (
            <span className="text-sm text-muted-foreground">
              {summary.tier === 'pro' ? '$49/mo' : '$199/mo'}
            </span>
          )}
        </div>
        <div className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{limitLabel}</span> leads per month
        </div>
        {summary.period_end && (
          <div className="text-xs text-muted-foreground">
            {summary.status === 'active' ? 'Renews' : 'Access until'}{' '}
            {new Date(summary.period_end).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
            {summary.days_remaining !== null && ` (${summary.days_remaining} days)`}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function BillingPage() {
  const { toast } = useToast()
  const searchParams = useSearchParams()
  const [loadingPriceId, setLoadingPriceId] = useState<string | null>(null)

  useEffect(() => {
    if (searchParams.get('session_id')) {
      toast({
        title: 'Subscription activated',
        description: "You're all set! Your plan has been upgraded.",
      })
    }

    if (searchParams.get('cancelled')) {
      toast({
        title: 'Checkout cancelled',
        description: 'No charge was made. You can upgrade any time.',
        variant: 'destructive',
      })
    }
  }, [searchParams, toast])

  const { data: summary, isLoading } = useQuery<BillingSummary>({
    queryKey: ['billing', 'summary'],
    queryFn: billingService.getSummary,
  })

  const checkoutMutation = useMutation({
    mutationFn: billingService.createCheckout,
    onSuccess: (url) => {
      window.location.href = url
    },
    onError: () => {
      setLoadingPriceId(null)
      toast({
        title: 'Checkout failed',
        description: 'Could not start checkout. Please try again.',
        variant: 'destructive',
      })
    },
  })

  const portalMutation = useMutation({
    mutationFn: billingService.createPortal,
    onSuccess: (url) => {
      window.location.href = url
    },
    onError: () => {
      toast({
        title: 'Could not open billing portal',
        description: 'Please try again in a moment.',
        variant: 'destructive',
      })
    },
  })

  const handleUpgrade = (priceId: string | null) => {
    if (!priceId) {
      toast({
        title: 'Plan unavailable',
        description: 'This Stripe price is not configured yet.',
        variant: 'destructive',
      })
      return
    }

    setLoadingPriceId(priceId)
    checkoutMutation.mutate(priceId)
  }

  const handleManageBilling = () => {
    portalMutation.mutate()
  }

  return (
    <div className="max-w-4xl space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Billing & Plans</h1>
        <p className="mt-1 text-muted-foreground">Manage your subscription and payment details.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {isLoading ? (
          <>
            <Skeleton className="h-36" />
            <Skeleton className="h-36" />
          </>
        ) : summary ? (
          <>
            <UsageMeter summary={summary} />
            {summary.has_active_subscription && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Billing management</CardTitle>
                  <CardDescription>
                    Update payment method, view invoices, or cancel your plan.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Button
                    variant="outline"
                    onClick={handleManageBilling}
                    disabled={portalMutation.isPending}
                  >
                    {portalMutation.isPending ? 'Opening portal...' : 'Manage billing'}
                  </Button>
                </CardContent>
              </Card>
            )}
          </>
        ) : null}
      </div>

      <div>
        <h2 className="mb-4 text-lg font-semibold">Available plans</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {TIERS.map((tier) => {
            const isCurrentTier = summary?.tier === tier.id
            const isPending = loadingPriceId === tier.priceId

            return (
              <Card
                key={tier.id}
                className={`relative flex flex-col ${tier.popular ? 'border-2 border-blue-500' : ''}`}
              >
                {tier.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge className="bg-blue-600 px-3 text-xs text-white">Most popular</Badge>
                  </div>
                )}

                <CardHeader className="pb-4">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <tier.icon className={`h-4 w-4 ${tier.color}`} />
                    {tier.name}
                  </CardTitle>
                  <CardDescription>{tier.description}</CardDescription>
                  <div className="flex items-baseline gap-1 pt-1">
                    <span className="text-2xl font-bold">{tier.price}</span>
                    <span className="text-sm text-muted-foreground">{tier.period}</span>
                  </div>
                </CardHeader>

                <CardContent className="flex flex-1 flex-col gap-4">
                  <ul className="flex-1 space-y-2">
                    {tier.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-2 text-sm">
                        <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-green-600" />
                        {feature}
                      </li>
                    ))}
                  </ul>

                  {isCurrentTier ? (
                    <Button variant="outline" disabled className="w-full">
                      Current plan
                    </Button>
                  ) : tier.priceId ? (
                    <Button
                      className="w-full"
                      onClick={() => handleUpgrade(tier.priceId)}
                      disabled={isPending || checkoutMutation.isPending}
                    >
                      {isPending ? 'Redirecting...' : `Upgrade to ${tier.name}`}
                    </Button>
                  ) : (
                    <Button variant="outline" className="w-full" disabled>
                      Free forever
                    </Button>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>

      {process.env.NODE_ENV === 'development' && (
        <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm">
          <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600" />
          <div>
            <p className="font-medium text-amber-800">Test mode active</p>
            <p className="mt-0.5 text-amber-700">
              Use card number <code className="font-mono">4242 4242 4242 4242</code> with any
              future expiry and any 3-digit CVC to test payments.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
