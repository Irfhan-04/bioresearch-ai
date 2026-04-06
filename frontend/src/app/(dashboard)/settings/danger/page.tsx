"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { useToast } from "@/components/ui/use-toast";
import { apiClient } from "@/lib/api/client";
import { useAuthStore } from "@/stores/auth-store";

export default function DangerPage() {
  const router = useRouter();
  const { toast } = useToast();
  const logout = useAuthStore((state) => state.logout);

  const [password, setPassword] = useState("");
  const [confirmText, setConfirmText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (confirmText !== "DELETE") return;
    if (!password) {
      toast({
        title: "Password required",
        description: "Enter your password to confirm deletion.",
        variant: "destructive",
      });
      return;
    }

    try {
      setIsDeleting(true);
      await apiClient.delete("/users/me", { data: { password } });
      logout();
      router.push("/");
    } catch (error: any) {
      const msg = error?.response?.data?.detail ?? "Deletion failed.";
      toast({ title: "Error", description: msg, variant: "destructive" });
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="mx-auto max-w-xl space-y-4 rounded-xl border border-red-200 bg-white p-6 shadow-sm">
      <h1 className="text-xl font-semibold text-red-700">Danger Zone</h1>
      <p className="text-sm text-gray-600">
        This action is irreversible. Type <strong>DELETE</strong> and enter your current
        password to permanently remove your account.
      </p>

      <input
        type="text"
        placeholder='Type "DELETE" to confirm'
        value={confirmText}
        onChange={(event) => setConfirmText(event.target.value)}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
      />

      <input
        type="password"
        placeholder="Enter your current password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
      />

      <button
        onClick={handleDelete}
        disabled={confirmText !== "DELETE" || isDeleting}
        className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {isDeleting ? "Deleting..." : "Delete Account"}
      </button>
    </div>
  );
}
