"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api/client";

interface Member {
  user_id: string;
  email: string;
  full_name: string | null;
  role: "admin" | "member" | "viewer";
  joined_at: string;
}

const ROLE_COLORS = {
  admin: "bg-purple-100 text-purple-700",
  member: "bg-blue-100 text-blue-700",
  viewer: "bg-gray-100 text-gray-600",
};

export function TeamMemberTable({ teamId }: { teamId: string }) {
  const queryClient = useQueryClient();
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");

  const { data: members = [] } = useQuery<Member[]>({
    queryKey: ["team", teamId, "members"],
    queryFn: () => apiClient.get(`/teams/${teamId}/members`).then((response) => response.data),
  });

  const invite = useMutation({
    mutationFn: (payload: { email: string; role: string }) => apiClient.post(`/teams/${teamId}/invitations`, payload),
    onSuccess: () => {
      setInviteEmail("");
      queryClient.invalidateQueries({ queryKey: ["team", teamId, "members"] });
    },
  });

  const changeRole = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      apiClient.patch(`/teams/${teamId}/members/${userId}/role`, { role }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["team", teamId, "members"] }),
  });

  const remove = useMutation({
    mutationFn: (userId: string) => apiClient.delete(`/teams/${teamId}/members/${userId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["team", teamId, "members"] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex gap-3">
        <input
          type="email"
          placeholder="colleague@company.com"
          value={inviteEmail}
          onChange={(event) => setInviteEmail(event.target.value)}
          className="flex-1 rounded-lg border px-3 py-2 text-sm"
        />
        <select
          value={inviteRole}
          onChange={(event) => setInviteRole(event.target.value)}
          className="rounded-lg border px-3 py-2 text-sm"
        >
          <option value="member">Member</option>
          <option value="admin">Admin</option>
          <option value="viewer">Viewer</option>
        </select>
        <button
          onClick={() => invite.mutate({ email: inviteEmail, role: inviteRole })}
          disabled={!inviteEmail || invite.isPending}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {invite.isPending ? "Sending…" : "Invite"}
        </button>
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-gray-500">
            <th className="pb-2">Member</th>
            <th className="pb-2">Role</th>
            <th className="pb-2">Joined</th>
            <th className="pb-2" />
          </tr>
        </thead>
        <tbody className="divide-y">
          {members.map((member) => (
            <tr key={member.user_id} className="py-3">
              <td className="py-3">
                <p className="font-medium">{member.full_name ?? "—"}</p>
                <p className="text-gray-400">{member.email}</p>
              </td>
              <td>
                <select
                  value={member.role}
                  onChange={(event) =>
                    changeRole.mutate({ userId: member.user_id, role: event.target.value })
                  }
                  className={`rounded px-2 py-1 text-xs font-medium ${ROLE_COLORS[member.role]}`}
                >
                  <option value="admin">Admin</option>
                  <option value="member">Member</option>
                  <option value="viewer">Viewer</option>
                </select>
              </td>
              <td className="text-gray-400">{new Date(member.joined_at).toLocaleDateString()}</td>
              <td>
                <button onClick={() => remove.mutate(member.user_id)} className="text-xs text-red-500 hover:text-red-700">
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
