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
import { useLead, useLeads } from '@/hooks/use-leads'
import { useParams, useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { Skeleton } from '@/components/ui/skeleton'

const schema = z.object({
  name:     z.string().min(2),
  title:    z.string().optional(),
  company:  z.string().optional(),
  email:    z.string().email().optional().or(z.literal('')),
  location: z.string().optional(),
  phone:    z.string().optional(),
  notes:    z.string().optional(),
  status:   z.enum(['NEW', 'CONTACTED', 'QUALIFIED', 'PROPOSAL', 'NEGOTIATION', 'WON', 'LOST']),
})
type EditLeadForm = z.infer<typeof schema>

export default function EditLeadPage() {
  const params = useParams()
  const id = params.id as string
  const router = useRouter()
  const { data: lead, isLoading } = useLead(id)
  const { updateLeadAsync, isUpdating } = useLeads()

  const { register, handleSubmit, setValue, formState: { errors } } = useForm<EditLeadForm>({
    resolver: zodResolver(schema),
  })

  useEffect(() => {
    if (lead) {
      setValue('name',     lead.name)
      setValue('title',    lead.title || '')
      setValue('company',  lead.company || '')
      setValue('email',    lead.email || '')
      setValue('location', lead.location || '')
      setValue('phone',    lead.phone || '')
      setValue('notes',    lead.notes || '')
      setValue('status',   lead.status)
    }
  }, [lead, setValue])

  const onSubmit = async (data: EditLeadForm) => {
    try {
      await updateLeadAsync(id, data)
      router.push(`/dashboard/leads/${id}`)
    } catch {
      // The mutation already surfaces the error to the user.
    }
  }

  if (isLoading) return (
    <div className="space-y-6 max-w-2xl">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-96 w-full" />
    </div>
  )

  if (!lead) return <div className="text-muted-foreground py-12 text-center">Lead not found.</div>

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-4">
        <Link href={`/dashboard/leads/${id}`}>
          <Button variant="ghost" size="icon"><ArrowLeft className="h-4 w-4" /></Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold">Edit Lead</h1>
          <p className="text-muted-foreground">{lead.name}</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Lead Information</CardTitle>
          <CardDescription>Update the details for this lead.</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Full Name *</Label>
              <Input {...register('name')} />
              {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Title</Label>
                <Input {...register('title')} />
              </div>
              <div className="space-y-2">
                <Label>Company</Label>
                <Input {...register('company')} />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Email</Label>
                <Input type="email" {...register('email')} />
              </div>
              <div className="space-y-2">
                <Label>Phone</Label>
                <Input {...register('phone')} />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Location</Label>
                <Input {...register('location')} />
              </div>
              <div className="space-y-2">
                <Label>Status</Label>
                <Select
                  defaultValue={lead.status}
                  onValueChange={(v) => setValue('status', v as EditLeadForm['status'])}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {['NEW', 'CONTACTED', 'QUALIFIED', 'PROPOSAL', 'NEGOTIATION', 'WON', 'LOST'].map((s) => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea rows={4} placeholder="Add any notes about this lead..." {...register('notes')} />
            </div>

            <div className="flex gap-2 pt-2">
              <Button type="submit" disabled={isUpdating}>
                {isUpdating
                  ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Saving...</>
                  : 'Save Changes'
                }
              </Button>
              <Link href={`/dashboard/leads/${id}`}>
                <Button variant="outline">Cancel</Button>
              </Link>
            </div>
          </CardContent>
        </form>
      </Card>
    </div>
  )
}
