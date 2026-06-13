interface LearningPathCardProps {
  title: string;
  sourceUrl: string;
  estimatedHours: number;
  rationale: string;
  citations?: string[];
}

export default function LearningPathCard({
  title,
  sourceUrl,
  estimatedHours,
  rationale,
  citations,
}: LearningPathCardProps) {
  return (
    <div className="card animate-fade-in flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-900 leading-snug">
          {title}
        </h3>
        <span className="shrink-0 rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
          {estimatedHours}h
        </span>
      </div>

      <p className="text-xs text-slate-500 leading-relaxed">{rationale}</p>

      {citations && citations.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {citations.map((url, i) => (
            <a
              key={i}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              title={url}
              className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-slate-100
                         text-xs font-medium text-slate-500 hover:bg-blue-100 hover:text-blue-700
                         transition-colors"
            >
              {i + 1}
            </a>
          ))}
        </div>
      )}

      <a
        href={sourceUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-auto inline-flex items-center gap-1.5 text-xs font-medium text-blue-600
                   hover:text-blue-800 hover:underline transition-colors"
      >
        Open resource
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="h-3.5 w-3.5"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M4.25 5.5a.75.75 0 00-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0
               00.75-.75v-4a.75.75 0 011.5 0v4A2.25 2.25 0 0112.75 17h-8.5A2.25 2.25
               0 012 14.75v-8.5A2.25 2.25 0 014.25 4h5a.75.75 0 010 1.5h-5z"
            clipRule="evenodd"
          />
          <path
            fillRule="evenodd"
            d="M6.194 12.753a.75.75 0 001.06.053L16.5 4.44v2.81a.75.75 0 001.5
               0v-4.5a.75.75 0 00-.75-.75h-4.5a.75.75 0 000 1.5h2.553l-9.056
               8.194a.75.75 0 00-.053 1.06z"
            clipRule="evenodd"
          />
        </svg>
      </a>
    </div>
  );
}
