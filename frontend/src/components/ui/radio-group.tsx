'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

function RadioGroup({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn('grid gap-2', className)}>{children}</div>
}

const RadioGroupItem = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement> & { value: string }
>(({ className, ...props }, ref) => <input ref={ref} type="radio" className={cn('h-4 w-4 accent-primary', className)} {...props} />)
RadioGroupItem.displayName = 'RadioGroupItem'

export { RadioGroup, RadioGroupItem }
