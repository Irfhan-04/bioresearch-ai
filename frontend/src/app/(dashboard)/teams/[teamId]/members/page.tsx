import { TeamMemberTable } from "@/components/teams/team-member-table";

export default function TeamMembersPage({ params }: { params: { teamId: string } }) {
  return <TeamMemberTable teamId={params.teamId} />;
}
