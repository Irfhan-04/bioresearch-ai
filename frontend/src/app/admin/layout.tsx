"use client";

import { redirect } from "next/navigation";

import { useAuthStore } from "@/stores/auth-store";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuthStore();

  if (!user) redirect("/login");
  if (!user.is_superuser) redirect("/dashboard");

  return (
    <div className="flex min-h-screen">
      <aside className="w-56 space-y-1 border-r bg-gray-50 p-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-400">Admin</p>
        {[
          { href: "/admin", label: "Overview" },
          { href: "/admin/users", label: "Users" },
          { href: "/admin/tickets", label: "Tickets" },
          { href: "/admin/flags", label: "Feature Flags" },
        ].map(({ href, label }) => (
          <a key={href} href={href} className="block rounded-lg px-3 py-2 text-sm font-medium hover:bg-gray-200">
            {label}
          </a>
        ))}
      </aside>
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
