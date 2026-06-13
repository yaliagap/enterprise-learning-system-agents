"use client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface StudySession {
  session_id?: string;
  date: string;
  hours: number;
  topics: string[];
  resource_ids?: string[];
  topic_hours?: number[];
}

interface StudyMilestone {
  milestone_id: string;
  domain_name: string;
  target_week: number;
  target_date: string;
  session_ids: string[];
}

interface StudyPlanTimelineProps {
  sessions: StudySession[];
  milestones?: StudyMilestone[];
}

// ---------------------------------------------------------------------------
// LP color palette (hex — exact values per spec)
// ---------------------------------------------------------------------------

const LP_HEX = ["#378ADD", "#1D9E75", "#BA7517", "#7F77DD", "#E0534A", "#26A69A"];

// ---------------------------------------------------------------------------
// Date helpers
// ---------------------------------------------------------------------------

function parseLocalDate(dateStr: string): Date {
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function weekIndex(dateStr: string, startStr: string): number {
  const diff =
    parseLocalDate(dateStr).getTime() - parseLocalDate(startStr).getTime();
  return Math.floor(diff / (7 * 86_400_000)) + 1;
}

function fmtDate(dateStr: string, opts: Intl.DateTimeFormatOptions): string {
  return parseLocalDate(dateStr).toLocaleDateString("en-US", opts);
}

function weekRangeLabel(days: [string, StudySession[]][]): string {
  const first = days[0][0];
  const last = days[days.length - 1][0];
  const a = fmtDate(first, { month: "short", day: "numeric" });
  const aMonth = fmtDate(first, { month: "short" });
  const bMonth = fmtDate(last, { month: "short" });
  const bDay = fmtDate(last, { day: "numeric" });
  return aMonth === bMonth
    ? `${a}–${bDay}`
    : `${a} – ${fmtDate(last, { month: "short", day: "numeric" })}`;
}

// ---------------------------------------------------------------------------
// Module card
// ---------------------------------------------------------------------------

interface ModuleCardProps {
  date: string;
  title: string;
  lpName: string;
  lpColor: string;
  hours: number;
}

function ModuleCard({ date, title, lpName, lpColor, hours }: ModuleCardProps) {
  const dayName = fmtDate(date, { weekday: "short" });
  const dayDate = fmtDate(date, { month: "short", day: "numeric" });
  const hoursLabel = Number.isInteger(hours) ? `${hours}h` : `${hours.toFixed(1)}h`;

  return (
    <div
      className="flex items-stretch rounded-lg overflow-hidden mb-2 border"
      style={{ background: "#151826", borderColor: "#2a2d3e" }}
    >
      {/* 4px LP color accent border */}
      <div className="w-1 shrink-0" style={{ backgroundColor: lpColor }} />

      <div className="flex flex-1 items-center gap-3 px-3 py-2.5">
        {/* Day + date */}
        <div className="shrink-0 w-10 text-center">
          <p
            className="text-xs font-bold uppercase leading-none"
            style={{ color: lpColor }}
          >
            {dayName}
          </p>
          <p className="text-xs text-slate-500 mt-0.5 leading-none">{dayDate}</p>
        </div>

        {/* Divider */}
        <div className="w-px self-stretch bg-slate-700 shrink-0" />

        {/* Title + LP name */}
        <div className="flex-1 min-w-0">
          <p className="text-sm text-slate-200 leading-snug">{title}</p>
          <p className="text-xs mt-0.5 font-medium" style={{ color: lpColor }}>
            {lpName}
          </p>
        </div>

        {/* Duration */}
        <span className="shrink-0 text-xs font-semibold text-slate-400 tabular-nums">
          {hoursLabel}
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Milestone badge
// ---------------------------------------------------------------------------

function MilestoneBadge({
  domain_name,
  target_date,
  color,
}: {
  domain_name: string;
  target_date: string;
  color: string;
}) {
  return (
    <div
      className="mt-3 flex items-center gap-2.5 rounded-lg px-3 py-2 border"
      style={{ background: color + "18", borderColor: color + "45" }}
    >
      <svg
        viewBox="0 0 20 20"
        fill="currentColor"
        className="h-4 w-4 shrink-0"
        style={{ color }}
      >
        <path
          fillRule="evenodd"
          d="M10 1a.75.75 0 01.75.75V4h3a.75.75 0 01.75.75v2.25a3.75 3.75 0 01-3.494 3.742A3.751 3.751 0 016.25 7V4.75A.75.75 0 017 4h3V1.75A.75.75 0 0110 1zm0 11a2.25 2.25 0 100-4.5 2.25 2.25 0 000 4.5zm-3.25 2h6.5a.75.75 0 010 1.5h-6.5a.75.75 0 010-1.5z"
          clipRule="evenodd"
        />
      </svg>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold leading-none" style={{ color }}>
          Milestone — {domain_name}
        </p>
        <p className="text-xs text-slate-500 mt-0.5">
          {fmtDate(target_date, {
            month: "short",
            day: "numeric",
            year: "numeric",
          })}
        </p>
      </div>
      <svg
        viewBox="0 0 16 16"
        fill="currentColor"
        className="h-4 w-4 shrink-0"
        style={{ color }}
      >
        <path
          fillRule="evenodd"
          d="M12.416 3.376a.75.75 0 010 1.06L6.666 10.19 3.583 7.107a.75.75 0 10-1.06 1.06l3.638 3.638a.75.75 0 001.06 0l6.256-6.37a.75.75 0 000-1.059z"
          clipRule="evenodd"
        />
      </svg>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Summary bar
// ---------------------------------------------------------------------------

function PlanSummary({ sessions }: { sessions: StudySession[] }) {
  const sorted = [...sessions].sort((a, b) => a.date.localeCompare(b.date));
  const totalHours =
    Math.round(sessions.reduce((s, x) => s + x.hours, 0) * 10) / 10;
  const startStr = sorted[0].date;
  const endStr = sorted[sorted.length - 1].date;
  const totalWeeks = weekIndex(endStr, startStr);

  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500 mb-5">
      <span className="font-semibold text-slate-300">{sessions.length} sessions</span>
      <span>·</span>
      <span>{totalHours}h</span>
      <span>·</span>
      <span>{totalWeeks} weeks</span>
      <span>·</span>
      <span>
        {fmtDate(startStr, { month: "short", day: "numeric" })} →{" "}
        {fmtDate(endStr, { month: "short", day: "numeric", year: "numeric" })}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function StudyPlanTimeline({
  sessions,
  milestones = [],
}: StudyPlanTimelineProps) {
  if (sessions.length === 0) {
    return (
      <p className="text-sm text-slate-500 italic">
        No study sessions scheduled yet.
      </p>
    );
  }

  // session_id → domain_name
  const sessionDomain = new Map<string, string>();
  milestones.forEach((m) =>
    m.session_ids.forEach((sid) => sessionDomain.set(sid, m.domain_name))
  );

  // domain_name → hex color (in milestone order)
  const lpColor = new Map<string, string>();
  milestones.forEach((m) => {
    if (!lpColor.has(m.domain_name)) {
      lpColor.set(m.domain_name, LP_HEX[lpColor.size % LP_HEX.length]);
    }
  });

  function resolveLP(session: StudySession): { name: string; hex: string } {
    const domain = session.session_id
      ? sessionDomain.get(session.session_id)
      : undefined;
    if (domain) return { name: domain, hex: lpColor.get(domain) ?? LP_HEX[0] };
    // Fallback: match any domain name appearing in topic text
    const topic = session.topics[0] ?? "";
    const found = Array.from(lpColor.entries()).find(([k]) => topic.includes(k));
    if (found) return { name: found[0], hex: found[1] };
    return { name: "Learning Path", hex: "#64748b" };
  }

  // Sort and group: week → day → sessions[]
  const sorted = [...sessions].sort((a, b) => a.date.localeCompare(b.date));
  const startDate = sorted[0].date;

  const weekMap = new Map<number, Map<string, StudySession[]>>();
  for (const s of sorted) {
    const wk = weekIndex(s.date, startDate);
    if (!weekMap.has(wk)) weekMap.set(wk, new Map());
    const dayMap = weekMap.get(wk)!;
    if (!dayMap.has(s.date)) dayMap.set(s.date, []);
    dayMap.get(s.date)!.push(s);
  }

  const weeks = Array.from(weekMap.entries()).sort(([a], [b]) => a - b);

  const milestoneByWeek = new Map<number, StudyMilestone>();
  milestones.forEach((m) => milestoneByWeek.set(m.target_week, m));

  return (
    <div>
      <PlanSummary sessions={sessions} />

      <div className="relative">
        {/* Continuous vertical spine */}
        <div
          className="absolute left-[17px] top-2 bottom-4 w-px"
          style={{ background: "#2a2d3e" }}
        />

        {weeks.map(([weekNum, dayMap]) => {
          const days = Array.from(dayMap.entries()).sort(([a], [b]) =>
            a.localeCompare(b)
          );
          const weekHours =
            Math.round(
              days.reduce(
                (s, [, ss]) => s + ss.reduce((a, b) => a + b.hours, 0),
                0
              ) * 10
            ) / 10;
          const milestone = milestoneByWeek.get(weekNum);

          return (
            <div key={weekNum} className="relative pl-10 mb-8">
              {/* Week dot on the spine */}
              <div
                className="absolute left-[13px] top-[5px] h-[9px] w-[9px] rounded-full border-2"
                style={{ background: "#0d0f1a", borderColor: "#4a4f6a" }}
              />

              {/* Week header */}
              <div className="flex items-baseline gap-2 mb-3">
                <span className="text-sm font-bold text-slate-200">
                  Week {weekNum}
                </span>
                <span className="text-slate-700">·</span>
                <span className="text-xs text-slate-400">
                  {weekRangeLabel(days)}
                </span>
                <span className="text-slate-700">·</span>
                <span className="text-xs font-medium text-slate-400">
                  {weekHours}h total
                </span>
              </div>

              {/* All module cards — zero truncation */}
              {days.flatMap(([dateStr, daySessions]) =>
                daySessions.flatMap((session, si) => {
                  const { name, hex } = resolveLP(session);
                  return session.topics.map((topic, ti) => {
                    const h =
                      session.topic_hours?.[ti] ??
                      Math.round((session.hours / Math.max(session.topics.length, 1)) * 10) / 10;
                    return (
                      <ModuleCard
                        key={`${session.session_id ?? `${dateStr}-${si}`}-${ti}`}
                        date={dateStr}
                        title={topic}
                        lpName={name}
                        lpColor={hex}
                        hours={h}
                      />
                    );
                  });
                })
              )}

              {/* Milestone badge when an LP completes this week */}
              {milestone && (
                <MilestoneBadge
                  domain_name={milestone.domain_name}
                  target_date={milestone.target_date}
                  color={lpColor.get(milestone.domain_name) ?? LP_HEX[0]}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
