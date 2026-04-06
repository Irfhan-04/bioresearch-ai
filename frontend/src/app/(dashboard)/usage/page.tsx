import { DailyActivityChart } from "@/components/usage/daily-activity-chart";
import { UsageMeter } from "@/components/usage/usage-meter";

export default function UsagePage() {
  return (
    <div className="mx-auto max-w-4xl space-y-8 px-4 py-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Usage & Quotas</h1>
        <p className="mt-1 text-sm text-gray-500">
          Your activity over the last 30 days and current quota usage.
        </p>
      </div>

      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-base font-semibold text-gray-700">Current Billing Period</h2>
        <UsageMeter />
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-700">Daily Activity — Last 30 Days</h2>
        </div>
        <DailyActivityChart days={30} />
      </section>
    </div>
  );
}
