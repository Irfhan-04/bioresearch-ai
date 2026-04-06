'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ExportDialog } from '@/components/leads/export-dialog'
import { FileText, FileSpreadsheet, FileJson } from 'lucide-react'

const formats = [
  {
    icon: FileText,
    title: 'CSV Export',
    description: 'Comma-separated values, compatible with Excel, Google Sheets, and any spreadsheet tool.',
    ext: 'csv',
  },
  {
    icon: FileSpreadsheet,
    title: 'Excel Export',
    description: 'Native .xlsx format with formatting. Best for sharing with non-technical stakeholders.',
    ext: 'xlsx',
  },
  {
    icon: FileJson,
    title: 'JSON Export',
    description: 'Full data structure including all fields. Ideal for API integrations and data pipelines.',
    ext: 'json',
  },
]

export default function ExportsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Exports</h1>
        <p className="text-muted-foreground">Download your lead data in multiple formats</p>
      </div>

      <div className="flex">
        <ExportDialog />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {formats.map((f) => (
          <Card key={f.ext}>
            <CardHeader className="flex flex-row items-center gap-3 pb-2">
              <f.icon className="h-6 w-6 text-primary" />
              <CardTitle className="text-base">{f.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>{f.description}</CardDescription>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}