'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ArrowLeft, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { useLeads } from '@/hooks/use-leads'
import { useRouter } from 'next/navigation'

const schema = z.object({
  name:     z.string().min(2, 'Name must be at least 2 characters'),
  title:    z.string().optional(),
  company:  z.string().optional(),
  email:    z.string().email('Invalid email').optional().or(z.literal('')),
  location: z.string().optional(),
})
type NewLeadForm = z.infer<typeof schema>

export default function NewLeadPage() {
  const { createLead, isCreating } = useLeads()
  const router = useRouter()

  const { register, handleSubmit, formState: { errors } } = useForm<NewLeadForm>({
    resolver: zodResolver(schema),
  })

  const onSubmit = (data: NewLeadForm) => {
    createLead({
      name:     data.name,
      title:    data.title || undefined,
      company:  data.company || undefined,
      email:    data.email || undefined,
      location: data.location || undefined,
    })
    router.push('/dashboard/leads')
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-4">
        <Link href="/dashboard/leads">
          <Button variant="ghost" size="icon"><ArrowLeft className="h-4 w-4" /></Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold">Add Lead</h1>
          <p className="text-muted-foreground">Create a new lead manually</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Lead Information</CardTitle>
          <CardDescription>Fill in the details for the new lead. Only name is required.</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Full Name *</Label>
              <Input placeholder="Dr. Jane Smith" {...register('name')} />
              {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Title</Label>
                <Input placeholder="Principal Scientist" {...register('title')} />
              </div>
              <div className="space-y-2">
                <Label>Company</Label>
                <Input placeholder="Genentech" {...register('company')} />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Email</Label>
                <Input type="email" placeholder="jane@example.com" {...register('email')} />
                {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
              </div>
              <div className="space-y-2">
                <Label>Location</Label>
                <Input placeholder="San Francisco, CA" {...register('location')} />
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <Button type="submit" disabled={isCreating}>
                {isCreating
                  ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Creating...</>
                  : 'Create Lead'
                }
              </Button>
              <Link href="/dashboard/leads">
                <Button variant="outline">Cancel</Button>
              </Link>
            </div>
          </CardContent>
        </form>
      </Card>
    </div>
  )
}