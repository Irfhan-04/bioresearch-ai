'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { ArrowLeft, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { useResearcher, useResearchers } from '@/hooks/use-researchers'
import { useParams, useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { Skeleton } from '@/components/ui/skeleton'

const schema = z.object({
  name: z.string().min(2),
  title: z.string().optional(),
  company: z.string().optional(),
  email: z.string().email().optional().or(z.literal('')),
  location: z.string().optional(),
  phone: z.string().optional(),
  notes: z.string().optional(),
  status: z.enum(['NEW', 'CONTACTED', 'QUALIFIED', 'PROPOSAL', 'NEGOTIATION', 'WON', 'LOST']),
})
type EditResearcherForm = z.infer<typeof schema>
const EDITABLE_STATUS = ['NEW', 'CONTACTED', 'QUALIFIED', 'PROPOSAL', 'NEGOTIATION', 'WON', 'LOST'] as const

export default function EditResearcherPage() {
  const params = useParams()
  const id = params.id as string
  const router = useRouter()
  const { data: researcher, isLoading } = useResearcher(id)
  const { updateResearcherAsync, isUpdating } = useResearchers()

  const { register, handleSubmit, setValue, formState: { errors } } = useForm<EditResearcherForm>({
    resolver: zodResolver(schema),
  })

  useEffect(() => {
    if (researcher) {
      setValue('name', researcher.name)
      setValue('title', researcher.title || '')
      setValue('company', researcher.company || '')
      setValue('email', researcher.email || '')
      setValue('location', researcher.location || '')
      setValue('phone', researcher.phone || '')
      setValue('notes', researcher.notes || '')
      const safeStatus = EDITABLE_STATUS.includes(researcher.status as EditResearcherForm['status'])
        ? (researcher.status as EditResearcherForm['status'])
        : 'NEW'
      setValue('status', safeStatus)
    }
  }, [researcher, setValue])

  const onSubmit = async (data: EditResearcherForm) => {
    await updateResearcherAsync(id, data)
    router.push(`/dashboard/researchers/${id}`)
  }

  if (isLoading) return <div className="space-y-6 max-w-2xl"><Skeleton className="h-8 w-48" /><Skeleton className="h-96 w-full" /></div>
  if (!researcher) return <div className="text-muted-foreground py-12 text-center">Researcher not found.</div>

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-4">
        <Link href={`/dashboard/researchers/${id}`}><Button variant="ghost" size="icon"><ArrowLeft className="h-4 w-4" /></Button></Link>
        <div><h1 className="text-3xl font-bold">Edit Researcher</h1><p className="text-muted-foreground">{researcher.name}</p></div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Researcher Information</CardTitle>
          <CardDescription>Update the details for this researcher.</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-4">
            <div className="space-y-2"><Label>Full Name *</Label><Input {...register('name')} />{errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}</div>
            <div className="grid gap-4 md:grid-cols-2"><div className="space-y-2"><Label>Title</Label><Input {...register('title')} /></div><div className="space-y-2"><Label>Company</Label><Input {...register('company')} /></div></div>
            <div className="grid gap-4 md:grid-cols-2"><div className="space-y-2"><Label>Email</Label><Input type="email" {...register('email')} /></div><div className="space-y-2"><Label>Phone</Label><Input {...register('phone')} /></div></div>
            <div className="grid gap-4 md:grid-cols-2"><div className="space-y-2"><Label>Location</Label><Input {...register('location')} /></div><div className="space-y-2"><Label>Status</Label><Select defaultValue={EDITABLE_STATUS.includes(researcher.status as EditResearcherForm['status']) ? (researcher.status as EditResearcherForm['status']) : 'NEW'} onValueChange={(v) => setValue('status', v as EditResearcherForm['status'])}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{EDITABLE_STATUS.map((s) => (<SelectItem key={s} value={s}>{s}</SelectItem>))}</SelectContent></Select></div></div>
            <div className="space-y-2"><Label>Notes</Label><Textarea rows={4} placeholder="Add any notes about this researcher..." {...register('notes')} /></div>
            <div className="flex gap-2 pt-2">
              <Button type="submit" disabled={isUpdating}>{isUpdating ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Saving...</> : 'Save Changes'}</Button>
              <Link href={`/dashboard/researchers/${id}`}><Button variant="outline">Cancel</Button></Link>
            </div>
          </CardContent>
        </form>
      </Card>
    </div>
  )
}
