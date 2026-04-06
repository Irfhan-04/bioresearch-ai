'use client'

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const defaultData = [
  { range: '0-20', count: 45 },
  { range: '21-40', count: 78 },
  { range: '41-60', count: 123 },
  { range: '61-80', count: 89 },
  { range: '81-100', count: 56 },
]

export function ScoreDistributionChart({ data }: { data?: typeof defaultData }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data || defaultData}>
        <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" vertical={false} />
        <XAxis axisLine={false} dataKey="range" tick={{ fill: '#71717a', fontSize: 12 }} tickLine={false} />
        <YAxis axisLine={false} tick={{ fill: '#71717a', fontSize: 12 }} tickLine={false} />
        <Tooltip
          cursor={{ fill: 'rgba(255,255,255,0.03)' }}
          contentStyle={{
            background: 'rgba(11,18,36,0.95)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '12px',
            color: '#e4e4e7',
          }}
        />
        <Bar dataKey="count" fill="#00d68f" radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
