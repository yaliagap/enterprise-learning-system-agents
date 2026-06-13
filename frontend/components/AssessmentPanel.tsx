interface Question {
  id: string;
  text: string;
  options: string[];
}

interface AssessmentResult {
  score: number;
  passed: boolean;
  weakAreas: string[];
  nextCertRecommendation?: string;
}

interface AssessmentPanelProps {
  questions: Question[];
  currentQuestionIndex: number;
  selectedAnswer: string | null;
  result: AssessmentResult | null;
  onSelectAnswer: (answer: string) => void;
  onSubmitAnswer: () => void;
  onBackToStudying: () => void;
}

/**
 * Interactive assessment panel shown when workflow_status === "assessing".
 *
 * Displays one question at a time with 4 answer options, a progress bar,
 * and a submit button. After all questions: shows score, pass/fail, weak areas.
 * Presentational — no business logic.
 */
export default function AssessmentPanel({
  questions,
  currentQuestionIndex,
  selectedAnswer,
  result,
  onSelectAnswer,
  onSubmitAnswer,
  onBackToStudying,
}: AssessmentPanelProps) {
  // Post-assessment result screen
  if (result !== null) {
    return (
      <div className="card animate-fade-in max-w-xl mx-auto">
        {/* Score ring */}
        <div className="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-full border-4 border-slate-200">
          <span
            className={`text-2xl font-bold ${
              result.passed ? "text-emerald-600" : "text-rose-600"
            }`}
          >
            {result.score}%
          </span>
        </div>

        <h2 className="text-center text-lg font-bold text-slate-900 mb-1">
          {result.passed ? "Congratulations!" : "Keep going!"}
        </h2>
        <p className="text-center text-sm text-slate-500 mb-4">
          {result.passed
            ? "You passed the assessment. Great work!"
            : "You didn't pass this time — review the weak areas and try again."}
        </p>

        {result.weakAreas.length > 0 && (
          <div className="mb-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              Areas to review
            </p>
            <div className="flex flex-wrap gap-2">
              {result.weakAreas.map((area) => (
                <span
                  key={area}
                  className="rounded-md bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700"
                >
                  {area}
                </span>
              ))}
            </div>
          </div>
        )}

        {result.passed && result.nextCertRecommendation && (
          <div className="mb-4 rounded-xl bg-emerald-50 p-4">
            <p className="text-xs font-semibold text-emerald-700 uppercase tracking-wide mb-1">
              Recommended next certification
            </p>
            <p className="text-sm font-bold text-emerald-900">
              {result.nextCertRecommendation}
            </p>
          </div>
        )}

        {!result.passed && (
          <button
            onClick={onBackToStudying}
            className="btn-primary w-full"
          >
            Back to studying
          </button>
        )}
      </div>
    );
  }

  const current = questions[currentQuestionIndex];
  if (!current) {
    return (
      <div className="card text-center text-sm text-slate-400 animate-pulse-slow">
        Loading question...
      </div>
    );
  }

  const total = questions.length;
  const progressPct = Math.round(((currentQuestionIndex + 1) / total) * 100);

  return (
    <div className="card animate-fade-in max-w-xl mx-auto">
      {/* Progress */}
      <div className="mb-4">
        <div className="flex justify-between text-xs text-slate-500 mb-1.5">
          <span>
            Question {currentQuestionIndex + 1} of {total}
          </span>
          <span>{progressPct}%</span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-slate-200">
          <div
            className="h-1.5 rounded-full bg-blue-500 transition-all duration-500"
            style={{ width: `${progressPct}%` }}
            role="progressbar"
            aria-valuenow={progressPct}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
      </div>

      {/* Question */}
      <p className="text-sm font-semibold text-slate-900 mb-4 leading-relaxed">
        {current.text}
      </p>

      {/* Options */}
      <fieldset className="space-y-2.5 mb-5">
        <legend className="sr-only">Answer options</legend>
        {current.options.map((option, idx) => {
          const isSelected = selectedAnswer === option;
          return (
            <label
              key={`${current.id}-option-${idx}`}
              className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm
                transition-colors ${
                  isSelected
                    ? "border-blue-500 bg-blue-50 text-blue-900"
                    : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                }`}
            >
              <input
                type="radio"
                name={`question-${current.id}`}
                value={option}
                checked={isSelected}
                onChange={() => onSelectAnswer(option)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500"
              />
              {option}
            </label>
          );
        })}
      </fieldset>

      <button
        onClick={onSubmitAnswer}
        disabled={selectedAnswer === null}
        className="btn-primary w-full"
      >
        Submit Answer
      </button>
    </div>
  );
}
