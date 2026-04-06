"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { apiClient } from "@/lib/api/client";

interface DailyRow {
  date: string;
  event_type: string;
  count: number;
}

interface ChartPoint {
  date: string;
  leads: number;
  searches: number;
  exports: number;
}

function buildChartData(rows: DailyRow[]): ChartPoint[] {
  const byDate: Record<string, ChartPoint> = {};

  rows.forEach(({ date, event_type, count }) => {
    const current =
      byDate[date] ?? (byDate[date] = { date, leads: 0, searches: 0, exports: 0 });

    if (event_type === "lead_created") current.leads += count;
    if (event_type === "search_executed") current.searches += count;
    if (event_type === "export_generated") current.exports += count;
  });

  return Object.values(byDate).sort((a, b) => a.date.localeCompare(b.date));
}

export function DailyActivityChart({ days = 30 }: { days?: number }) {
  const { data: rows = [], isLoading } = useQuery<DailyRow[]>({
    queryKey: ["analytics", "daily", days],
    queryFn: () =>
      apiClient.get(`/analytics/me/daily?days=${days}`).then((response) => response.data),
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return <div className="h-64 w-full animate-pulse rounded-xl bg-gray-100" />;
  }

  const chartData = buildChartData(rows);

  if (chartData.length === 0) {
    return (
      <div className="flex h-64 w-full items-center justify-center rounded-xl border border-dashed border-gray-200">
        <p className="text-sm text-gray-400">No activity in the last {days} days</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={chartData} margin={{ top: 4, right: 16, left: -8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11 }}
          tickFormatter={(value: string) => {
            const dt = new Date(value);
            return `${dt.getMonth() + 1}/${dt.getDate()}`;
          }}
          interval="preserveStartEnd"
        />
        <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
        <Tooltip
          labelFormatter={(label: string) =>
            new Date(label).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
            })
          }
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="leads" name="Leads Created" fill="#6366f1" radius={[3, 3, 0, 0]} />
        <Bar dataKey="searches" name="Searches" fill="#10b981" radius={[3, 3, 0, 0]} />
        <Bar dataKey="exports" name="Exports" fill="#f59e0b" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
