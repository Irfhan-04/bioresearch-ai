'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

type CheckboxProps = React.InputHTMLAttributes<HTMLInputElement> & {
  onCheckedChange?: (checked: boolean) => void
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, checked, onCheckedChange, onChange, ...props }, ref) => (
    <input
      ref={ref}
      type="checkbox"
      className={cn('h-4 w-4 rounded border border-input accent-primary', className)}
      checked={!!checked}
      onChange={(e) => {
        onChange?.(e)
        onCheckedChange?.(e.target.checked)
      }}
      {...props}
    />
  )
)
Checkbox.displayName = 'Checkbox'

export { Checkbox }
