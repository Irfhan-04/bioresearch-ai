'use client'

import { useState } from 'react'
import { Download, Loader2 } from 'lucide-react'

import { Checkbox } from '@/components/ui/checkbox'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { useToast } from '@/components/ui/use-toast'
import { apiClient } from '@/lib/api/client'

const FIELDS = [
  { id: 'name', label: 'Name' },
  { id: 'email', label: 'Email' },
  { id: 'company', label: 'Company' },
  { id: 'title', label: 'Title' },
  { id: 'location', label: 'Location' },
  { id: 'propensity_score', label: 'Score' },
  { id: 'status', label: 'Status' },
  { id: 'phone', label: 'Phone' },
  { id: 'linkedin_url', label: 'LinkedIn' },
] as const

const EXPORT_FORMATS = [
  { id: 'csv', label: 'CSV (.csv)' },
  { id: 'xlsx', label: 'Excel (.xlsx)' },
  { id: 'json', label: 'JSON (.json)' },
] as const

type ExportField = (typeof FIELDS)[number]['id']
type ExportFormat = (typeof EXPORT_FORMATS)[number]['id']

export function ExportDialog() {
  const [open, setOpen] = useState(false)
  const [format, setFormat] = useState<ExportFormat>('csv')
  const [fields, setFields] = useState<ExportField[]>(FIELDS.map((field) => field.id))
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()

  const toggle = (id: ExportField) => {
    setFields((prev) => (prev.includes(id) ? prev.filter((value) => value !== id) : [...prev, id]))
  }

  const handleExport = async () => {
    setLoading(true)

    try {
      const response = await apiClient.post('/export', { format, fields }, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')

      link.href = url
      link.download = `leads.${format}`
      document.body.appendChild(link)
      link.click()
      link.remove()

      toast({ title: 'Exported!', description: 'Your file is downloading.' })
      setOpen(false)
    } catch {
      toast({ title: 'Error', description: 'Export failed', variant: 'destructive' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">
          <Download className="mr-2 h-4 w-4" />
          Export
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Export Leads</DialogTitle>
          <DialogDescription>Choose format and fields to export</DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          <div className="space-y-2">
            <Label>Format</Label>
            <div className="space-y-2">
              {EXPORT_FORMATS.map((option) => (
                <div key={option.id} className="flex items-center space-x-2">
                  <input
                    type="radio"
                    name="export-format"
                    value={option.id}
                    id={option.id}
                    checked={format === option.id}
                    onChange={() => setFormat(option.id)}
                    className="h-4 w-4 accent-primary"
                  />
                  <Label htmlFor={option.id} className="cursor-pointer font-normal">
                    {option.label}
                  </Label>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <Label>Fields to Include</Label>
            <div className="grid grid-cols-2 gap-2">
              {FIELDS.map((field) => (
                <div key={field.id} className="flex items-center space-x-2">
                  <Checkbox
                    id={field.id}
                    checked={fields.includes(field.id)}
                    onCheckedChange={() => toggle(field.id)}
                  />
                  <Label htmlFor={field.id} className="cursor-pointer text-sm font-normal">
                    {field.label}
                  </Label>
                </div>
              ))}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleExport} disabled={loading}>
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4" />
                Export
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
