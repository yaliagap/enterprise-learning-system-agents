interface ReadinessIndicators {
  hoursStudied: number;
  resourcesCompleted: number;
  totalResources: number;
}

interface HITLConfirmationProps {
  indicators: ReadinessIndicators;
  onConfirm: () => void;
  onDecline: () => void;
}

/**
 * Full-screen overlay shown when workflow_status === "awaiting_assessment".
 *
 * This component is rendered via useCopilotAction with renderAndWaitForResponse.
 * The parent page wires onConfirm/onDecline to the CopilotKit action response handler.
 * Presentational — no business logic.
 */
export default function HITLConfirmation({
  indicators,
  onConfirm,
  onDecline,
}: HITLConfirmationProps) {
  const completionPct =
    indicators.totalResources > 0
      ? Math.round(
          (indicators.resourcesCompleted / indicators.totalResources) * 100
        )
      : 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60
                 backdrop-blur-sm animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="hitl-title"
    >
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-2xl animate-slide-up">
        {/* Icon */}
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-violet-100">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            className="h-7 w-7 text-violet-600"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4.5 12.75l6 6 9-13.5"
            />
          </svg>
        </div>

        <h2
          id="hitl-title"
          className="text-center text-xl font-bold text-slate-900 mb-2"
        >
          Study plan complete
        </h2>
        <p className="text-center text-sm text-slate-500 mb-6">
          You&apos;ve completed your study plan. Are you ready to be assessed?
        </p>

        {/* Readiness indicators */}
        <div className="mb-6 grid grid-cols-2 gap-3">
          <div className="rounded-xl bg-slate-50 p-4 text-center">
            <p className="text-2xl font-bold text-slate-900">
              {indicators.hoursStudied}h
            </p>
            <p className="text-xs text-slate-500 mt-0.5">Hours studied</p>
          </div>
          <div className="rounded-xl bg-slate-50 p-4 text-center">
            <p className="text-2xl font-bold text-slate-900">{completionPct}%</p>
            <p className="text-xs text-slate-500 mt-0.5">Resources completed</p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mb-6">
          <div className="mb-1.5 flex justify-between text-xs text-slate-500">
            <span>Progress</span>
            <span>
              {indicators.resourcesCompleted} / {indicators.totalResources}
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-slate-200">
            <div
              className="h-2 rounded-full bg-violet-500 transition-all duration-700"
              style={{ width: `${completionPct}%` }}
              role="progressbar"
              aria-valuenow={completionPct}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
        </div>

        {/* CTA buttons */}
        <div className="flex flex-col gap-3 sm:flex-row">
          <button
            onClick={onConfirm}
            className="btn-primary flex-1 text-center"
            aria-label="Confirm readiness and start assessment"
          >
            Yes, I&apos;m ready
          </button>
          <button
            onClick={onDecline}
            className="btn-secondary flex-1 text-center"
            aria-label="Decline assessment and continue studying"
          >
            Not yet, continue studying
          </button>
        </div>
      </div>
    </div>
  );
}
