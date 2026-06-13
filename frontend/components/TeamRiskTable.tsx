type LearnerStatus = "On Track" | "At Risk" | "Completed";

interface TeamMember {
  anonymizedId: string; // e.g. "Learner A"
  status: LearnerStatus;
  hoursStudied: number;
  readinessScore: number;
  targetCert: string;
}

interface TeamRiskTableProps {
  members: TeamMember[];
}

const STATUS_STYLES: Record<LearnerStatus, string> = {
  "On Track": "bg-emerald-50 text-emerald-700",
  "At Risk": "bg-rose-50 text-rose-700",
  Completed: "bg-blue-50 text-blue-700",
};

/**
 * Table of anonymized team members with their learning status.
 * Presentational — no business logic, no raw PII.
 */
export default function TeamRiskTable({ members }: TeamRiskTableProps) {
  if (members.length === 0) {
    return (
      <p className="text-sm text-slate-400 italic">No team data available.</p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50">
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              Learner
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              Status
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              Certification
            </th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
              Hours
            </th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
              Readiness
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {members.map((member) => (
            <tr
              key={member.anonymizedId}
              className="hover:bg-slate-50 transition-colors"
            >
              <td className="px-4 py-3 font-medium text-slate-900">
                {member.anonymizedId}
              </td>
              <td className="px-4 py-3">
                <span
                  className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold
                    ${STATUS_STYLES[member.status]}`}
                >
                  {member.status}
                </span>
              </td>
              <td className="px-4 py-3 text-slate-600">{member.targetCert}</td>
              <td className="px-4 py-3 text-right text-slate-600">
                {member.hoursStudied}h
              </td>
              <td className="px-4 py-3 text-right">
                <span
                  className={`font-semibold ${
                    member.readinessScore >= 70
                      ? "text-emerald-600"
                      : member.readinessScore >= 50
                      ? "text-amber-600"
                      : "text-rose-600"
                  }`}
                >
                  {member.readinessScore}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
