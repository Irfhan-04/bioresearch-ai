'use client'

import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const defaultData = [
  { date: 'Jan', created: 65, indexed: 28 },
  { date: 'Feb', created: 78, indexed: 35 },
  { date: 'Mar', created: 89, indexed: 42 },
  { date: 'Apr', created: 95, indexed: 51 },
  { date: 'May', created: 112, indexed: 67 },
  { date: 'Jun', created: 134, indexed: 78 },
]

export function ResearchersTimelineChart({ data }: { data?: typeof defaultData }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data || defaultData}>
        <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" vertical={false} />
        <XAxis axisLine={false} dataKey="date" tick={{ fill: '#71717a', fontSize: 12 }} tickLine={false} />
        <YAxis axisLine={false} tick={{ fill: '#71717a', fontSize: 12 }} tickLine={false} />
        <Tooltip
          contentStyle={{
            background: 'rgba(11,18,36,0.95)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '12px',
            color: '#e4e4e7',
          }}
        />
        <Legend wrapperStyle={{ color: '#a1a1aa', fontSize: '12px' }} />
        <Line
          type="monotone"
          dataKey="created"
          stroke="#00d68f"
          strokeWidth={2.5}
          dot={{ r: 0 }}
          activeDot={{ r: 5, fill: '#00d68f' }}
          name="Researchers Indexed"
        />
        <Line
          type="monotone"
          dataKey="indexed"
          stroke="#a78bfa"
          strokeWidth={2.5}
          dot={{ r: 0 }}
          activeDot={{ r: 5, fill: '#a78bfa' }}
          name="Researchers"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
