interface ReadinessGaugeProps {
  score: number; // 0–100
  label?: string;
  size?: "sm" | "md" | "lg";
}

const SIZE_MAP = {
  sm: { svg: 80, strokeWidth: 8, textClass: "text-base" },
  md: { svg: 120, strokeWidth: 10, textClass: "text-2xl" },
  lg: { svg: 160, strokeWidth: 12, textClass: "text-3xl" },
};

function scoreColor(score: number): string {
  if (score >= 80) return "#10b981"; // emerald-500
  if (score >= 60) return "#f59e0b"; // amber-500
  return "#ef4444"; // red-500
}

/**
 * Circular SVG gauge showing a readiness score (0–100).
 * Uses a stroke-dashoffset technique — no external chart library needed.
 * Presentational — no business logic.
 */
export default function ReadinessGauge({
  score,
  label = "Readiness",
  size = "md",
}: ReadinessGaugeProps) {
  const { svg: diameter, strokeWidth, textClass } = SIZE_MAP[size];
  const radius = (diameter - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clampedScore = Math.min(100, Math.max(0, score));
  const offset = circumference - (clampedScore / 100) * circumference;
  const color = scoreColor(clampedScore);
  const cx = diameter / 2;
  const cy = diameter / 2;

  return (
    <div className="flex flex-col items-center gap-1.5" aria-label={`${label}: ${clampedScore}%`}>
      <svg
        width={diameter}
        height={diameter}
        viewBox={`0 0 ${diameter} ${diameter}`}
        className="-rotate-90"
        aria-hidden="true"
      >
        {/* Track */}
        <circle
          cx={cx}
          cy={cy}
          r={radius}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={strokeWidth}
        />
        {/* Progress arc */}
        <circle
          cx={cx}
          cy={cy}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.8s ease-out" }}
        />
        {/* Score text — counter-rotate so it reads upright */}
        <text
          x={cx}
          y={cy}
          textAnchor="middle"
          dominantBaseline="middle"
          className={`font-bold fill-slate-900 ${textClass}`}
          style={{ transform: `rotate(90deg)`, transformOrigin: `${cx}px ${cy}px` }}
        >
          {clampedScore}%
        </text>
      </svg>
      <p className="text-xs font-medium text-slate-500">{label}</p>
    </div>
  );
}
