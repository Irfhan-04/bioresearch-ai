"use client";

import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface AreaBucket {
  area: string
  count: number
}

interface Props {
  data: AreaBucket[]
}

const AREA_COLORS: Record<string, string> = {
  toxicology: '#00f5d4',
  drug_safety: '#00bbf9',
  drug_discovery: '#fee440',
  organoids: '#9b5de5',
  in_vitro: '#f15bb5',
  biomarkers: '#00c49a',
  preclinical: '#f9c74f',
  general_biotech: '#577590',
}

const AREA_LABELS: Record<string, string> = {
  toxicology: 'Toxicology',
  drug_safety: 'Drug Safety',
  drug_discovery: 'Drug Discovery',
  organoids: 'Organoids',
  in_vitro: 'In Vitro',
  biomarkers: 'Biomarkers',
  preclinical: 'Preclinical',
  general_biotech: 'General Biotech',
}

export function ResearchAreaDonutChart({ data }: Props) {
  if (!data || data.length === 0) {
    return <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">No researchers indexed yet.</div>
  }

  const chartData = data.map((d) => ({
    name: AREA_LABELS[d.area] ?? d.area,
    value: d.count,
    color: AREA_COLORS[d.area] ?? '#64748b',
  }))

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={chartData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} paddingAngle={3} dataKey="value">
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: '6px',
              fontSize: '12px',
            }}
            formatter={(value: number, name: string) => [`${value} researcher${value !== 1 ? 's' : ''}`, name]}
          />
          <Legend
            formatter={(value) => (
              <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
                {value}
              </span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
