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
import { useResearchers } from '@/hooks/use-researchers'
import { useRouter } from 'next/navigation'

const schema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  title: z.string().optional(),
  company: z.string().optional(),
  email: z.string().email('Invalid email').optional().or(z.literal('')),
  location: z.string().optional(),
})
type NewResearcherForm = z.infer<typeof schema>

export default function NewResearcherPage() {
  const { createResearcher, isCreating } = useResearchers()
  const router = useRouter()

  const { register, handleSubmit, formState: { errors } } = useForm<NewResearcherForm>({
    resolver: zodResolver(schema),
  })

  const onSubmit = (data: NewResearcherForm) => {
    createResearcher(data)
    router.push('/dashboard/researchers')
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-4">
        <Link href="/dashboard/researchers"><Button variant="ghost" size="icon"><ArrowLeft className="h-4 w-4" /></Button></Link>
        <div><h1 className="text-3xl font-bold">Add Researcher</h1><p className="text-muted-foreground">Create a new researcher manually</p></div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Researcher Information</CardTitle>
          <CardDescription>Fill in the details for the new researcher. Only name is required.</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-4">
            <div className="space-y-2"><Label>Researcher *</Label><Input placeholder="Dr. Jane Smith" {...register('name')} />{errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}</div>
            <div className="grid gap-4 md:grid-cols-2"><div className="space-y-2"><Label>Title</Label><Input placeholder="Principal Scientist" {...register('title')} /></div><div className="space-y-2"><Label>Organization</Label><Input placeholder="Genentech" {...register('company')} /></div></div>
            <div className="grid gap-4 md:grid-cols-2"><div className="space-y-2"><Label>Contact Email</Label><Input type="email" placeholder="jane@example.com" {...register('email')} />{errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}</div><div className="space-y-2"><Label>Location</Label><Input placeholder="San Francisco, CA" {...register('location')} /></div></div>
            <div className="flex gap-2 pt-2">
              <Button type="submit" disabled={isCreating}>{isCreating ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Creating...</> : 'Create Researcher'}</Button>
              <Link href="/dashboard/researchers"><Button variant="outline">Cancel</Button></Link>
            </div>
          </CardContent>
        </form>
      </Card>
    </div>
  )
}
