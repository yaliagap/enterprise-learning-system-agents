"use client";

import { useState } from "react";
import type { AssessmentAnswers, AssessmentQuestion } from "@/app/lib/assessment-types";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ExamInterfaceProps {
  questions: AssessmentQuestion[];
  onSubmit: (answers: AssessmentAnswers) => void;
}

// ---------------------------------------------------------------------------
// QuestionCard — renders the input controls for one question
// ---------------------------------------------------------------------------

interface QuestionCardProps {
  question: AssessmentQuestion;
  selected: string[];
  onAnswer: (answers: string[]) => void;
}

function QuestionCard({ question, selected, onAnswer }: QuestionCardProps) {
  function toggleCheckbox(option: string) {
    if (selected.includes(option)) {
      onAnswer(selected.filter((a) => a !== option));
    } else if (selected.length < question.correct_answer_count) {
      onAnswer([...selected, option]);
    }
  }

  if (question.question_type === "true_false") {
    return (
      <div className="flex gap-3 mt-4">
        {["True", "False"].map((val) => {
          const isSelected = selected[0] === val;
          return (
            <button
              key={val}
              type="button"
              onClick={() => onAnswer([val])}
              className={`flex-1 rounded-xl border-2 py-4 text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
                ${isSelected
                  ? "border-blue-600 bg-blue-600 text-white"
                  : "border-slate-300 bg-white text-slate-700 hover:border-blue-400 hover:text-blue-600"
                }`}
              aria-pressed={isSelected}
            >
              {val}
            </button>
          );
        })}
      </div>
    );
  }

  if (question.question_type === "multi_select") {
    return (
      <fieldset className="space-y-2.5 mt-4">
        <legend className="text-xs font-medium text-slate-500 mb-2">
          Select {question.correct_answer_count} answer{question.correct_answer_count !== 1 ? "s" : ""}{" "}
          <span className={selected.length >= question.correct_answer_count ? "text-emerald-600 font-semibold" : "text-slate-400"}>
            ({selected.length}/{question.correct_answer_count})
          </span>
        </legend>
        {question.options.map((option, idx) => {
          const isSelected = selected.includes(option);
          return (
            <label
              key={`${question.id}-opt-${idx}`}
              className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm transition-colors
                ${isSelected
                  ? "border-blue-500 bg-blue-50 text-blue-900"
                  : selected.length >= question.correct_answer_count
                  ? "border-slate-200 bg-white text-slate-400 cursor-not-allowed opacity-60"
                  : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                }`}
            >
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => toggleCheckbox(option)}
                className="h-4 w-4 rounded text-blue-600 focus:ring-blue-500"
              />
              {option}
            </label>
          );
        })}
      </fieldset>
    );
  }

  // multiple_choice — radio buttons
  return (
    <fieldset className="space-y-2.5 mt-4">
      <legend className="sr-only">Answer options</legend>
      {question.options.map((option, idx) => {
        const isSelected = selected[0] === option;
        return (
          <label
            key={`${question.id}-opt-${idx}`}
            className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm transition-colors
              ${isSelected
                ? "border-blue-500 bg-blue-50 text-blue-900"
                : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              }`}
          >
            <input
              type="radio"
              name={`question-${question.id}`}
              value={option}
              checked={isSelected}
              onChange={() => onAnswer([option])}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500"
            />
            {option}
          </label>
        );
      })}
    </fieldset>
  );
}

// ---------------------------------------------------------------------------
// QuestionNavigator — 15-button grid
// ---------------------------------------------------------------------------

type QuestionStatus = "unanswered" | "answered" | "review";

interface QuestionNavigatorProps {
  total: number;
  currentIndex: number;
  answeredIds: Set<string>;
  markedIds: Set<string>;
  questions: AssessmentQuestion[];
  onJump: (index: number) => void;
}

function QuestionNavigator({
  total,
  currentIndex,
  answeredIds,
  markedIds,
  questions,
  onJump,
}: QuestionNavigatorProps) {
  function getStatus(index: number): QuestionStatus {
    const q = questions[index];
    if (!q) return "unanswered";
    if (markedIds.has(q.id)) return "review";
    if (answeredIds.has(q.id)) return "answered";
    return "unanswered";
  }

  const colorMap: Record<QuestionStatus, string> = {
    unanswered: "bg-slate-200 text-slate-700 hover:bg-slate-300",
    answered: "bg-blue-600 text-white hover:bg-blue-700",
    review: "bg-amber-400 text-white hover:bg-amber-500",
  };

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-2">
        Questions
      </p>
      <div className="flex flex-wrap gap-1.5">
        {Array.from({ length: total }, (_, i) => {
          const status = getStatus(i);
          const isCurrent = i === currentIndex;
          return (
            <button
              key={i}
              type="button"
              onClick={() => onJump(i)}
              aria-label={`Question ${i + 1} — ${status}${isCurrent ? " (current)" : ""}`}
              className={`h-8 w-8 rounded-md text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-copilot-500 focus:ring-offset-1
                ${colorMap[status]}
                ${isCurrent ? "ring-2 ring-copilot-700 ring-offset-1" : ""}
              `}
            >
              {i + 1}
            </button>
          );
        })}
      </div>
      <div className="flex gap-3 mt-3 text-xs text-slate-500">
        <span className="flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded bg-slate-200 inline-block" />
          Unanswered
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded bg-copilot-600 inline-block" />
          Answered
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded bg-amber-400 inline-block" />
          Review
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ReviewOverview — shown before final submission
// ---------------------------------------------------------------------------

interface ReviewOverviewProps {
  questions: AssessmentQuestion[];
  unansweredIds: string[];
  markedIds: Set<string>;
  onGoBack: () => void;
  onConfirmSubmit: () => void;
}

function ReviewOverview({
  questions,
  unansweredIds,
  markedIds,
  onGoBack,
  onConfirmSubmit,
}: ReviewOverviewProps) {
  const unanswered = questions.filter((q) => unansweredIds.includes(q.id));
  const marked = questions.filter((q) => markedIds.has(q.id));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="card max-w-md w-full mx-4 animate-fade-in">
        <h2 className="text-base font-bold text-slate-900 mb-1">Review before submitting</h2>
        <p className="text-xs text-slate-500 mb-4">
          Check your answers before final submission.
        </p>

        {unanswered.length > 0 && (
          <div className="mb-4">
            <p className="text-xs font-semibold text-rose-600 uppercase tracking-wide mb-2">
              Unanswered ({unanswered.length})
            </p>
            <div className="space-y-1">
              {unanswered.map((q) => (
                <p key={q.id} className="text-xs text-slate-700">
                  • Q{questions.indexOf(q) + 1}: {q.text.slice(0, 60)}
                  {q.text.length > 60 ? "…" : ""}
                </p>
              ))}
            </div>
          </div>
        )}

        {marked.length > 0 && (
          <div className="mb-4">
            <p className="text-xs font-semibold text-amber-600 uppercase tracking-wide mb-2">
              Marked for review ({marked.length})
            </p>
            <div className="space-y-1">
              {marked.map((q) => (
                <p key={q.id} className="text-xs text-slate-700">
                  • Q{questions.indexOf(q) + 1}: {q.text.slice(0, 60)}
                  {q.text.length > 60 ? "…" : ""}
                </p>
              ))}
            </div>
          </div>
        )}

        {unanswered.length === 0 && marked.length === 0 && (
          <p className="text-xs text-emerald-600 mb-4">
            All questions answered and none marked for review.
          </p>
        )}

        <div className="flex gap-3 mt-4">
          <button type="button" onClick={onGoBack} className="btn-secondary flex-1">
            Go back
          </button>
          <button type="button" onClick={onConfirmSubmit} className="btn-primary flex-1">
            Submit anyway
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ExamInterface — main component
// ---------------------------------------------------------------------------

export default function ExamInterface({ questions, onSubmit }: ExamInterfaceProps) {
  const [answers, setAnswers] = useState<Map<string, string[]>>(new Map());
  const [markedForReview, setMarkedForReview] = useState<Set<string>>(new Set());
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showReview, setShowReview] = useState(false);

  const currentQuestion = questions[currentIndex];
  const currentAnswers = currentQuestion ? (answers.get(currentQuestion.id) ?? []) : [];
  const answeredIds = new Set(
    questions
      .filter((q) => {
        const vals = answers.get(q.id) ?? [];
        return q.question_type === "multi_select"
          ? vals.length >= q.correct_answer_count
          : vals.length > 0;
      })
      .map((q) => q.id)
  );
  const allAnswered = questions.length > 0 && answeredIds.size === questions.length;
  const unansweredIds = questions
    .filter((q) => !answeredIds.has(q.id))
    .map((q) => q.id);

  const currentFullyAnswered = currentQuestion
    ? currentQuestion.question_type === "multi_select"
      ? currentAnswers.length >= currentQuestion.correct_answer_count
      : currentAnswers.length > 0
    : false;

  function handleAnswer(questionId: string, selected: string[]) {
    setAnswers((prev) => {
      const next = new Map(prev);
      next.set(questionId, selected);
      return next;
    });
  }

  function toggleMarkForReview(questionId: string) {
    setMarkedForReview((prev) => {
      const next = new Set(prev);
      if (next.has(questionId)) {
        next.delete(questionId);
      } else {
        next.add(questionId);
      }
      return next;
    });
  }

  function handleSubmitClick() {
    setShowReview(true);
  }

  function handleConfirmSubmit() {
    const answerList = questions.map((q) => ({
      question_id: q.id,
      selected_answers: answers.get(q.id) ?? [],
    }));
    onSubmit({ answers: answerList });
  }

  if (!currentQuestion) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm text-slate-400 animate-pulse">Loading questions…</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Exam header */}
      <div className="shrink-0 bg-violet-600 text-white px-6 py-3 text-center">
        <p className="text-xs font-semibold uppercase tracking-widest">
          You must complete this assessment to continue
        </p>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left panel — question */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {/* Progress */}
          <div className="mb-5">
            <div className="flex items-center justify-between text-xs text-slate-500 mb-1.5">
              <span className="font-semibold">
                Question {currentIndex + 1} of {questions.length}
              </span>
              <span className="capitalize text-slate-400">
                {currentQuestion.difficulty} · {currentQuestion.domain}
              </span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-slate-200">
              <div
                className="h-1.5 rounded-full bg-violet-500 transition-all duration-300"
                style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
                role="progressbar"
                aria-valuenow={currentIndex + 1}
                aria-valuemin={1}
                aria-valuemax={questions.length}
              />
            </div>
          </div>

          {/* Scenario context block (scenario-based questions only) */}
          {currentQuestion.is_scenario_based && currentQuestion.scenario_context && (
            <div className="mb-3 rounded-xl border border-slate-200 bg-slate-50 px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-2">Scenario</p>
              <p className="text-sm text-slate-700 leading-relaxed">{currentQuestion.scenario_context}</p>
            </div>
          )}

          {/* Question text */}
          <div className="card mb-4 border-l-4 border-blue-500">
            <div className="flex items-center gap-2 mb-2">
              <span className={`rounded-full px-2 py-0.5 text-xs font-semibold
                ${{
                  easy: "bg-emerald-100 text-emerald-700",
                  medium: "bg-amber-100 text-amber-700",
                  hard: "bg-rose-100 text-rose-700",
                }[currentQuestion.difficulty] ?? "bg-slate-100 text-slate-600"}`}>
                {currentQuestion.difficulty}
              </span>
              <span className="rounded-full bg-violet-100 px-2 py-0.5 text-xs font-semibold text-violet-700">
                {currentQuestion.bloom_level}
              </span>
              {currentQuestion.is_scenario_based && (
                <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
                  Scenario
                </span>
              )}
            </div>
            <p className="text-base font-semibold text-slate-900 leading-relaxed mb-1">
              {currentQuestion.text}
            </p>
            <p className="text-xs text-slate-400">{currentQuestion.domain} · {(currentQuestion.exam_weight_pct * 100).toFixed(0)}% of exam</p>

            <QuestionCard
              question={currentQuestion}
              selected={currentAnswers}
              onAnswer={(sel) => handleAnswer(currentQuestion.id, sel)}
            />

            {/* Mark for review */}
            <label className="flex items-center gap-2 mt-4 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={markedForReview.has(currentQuestion.id)}
                onChange={() => toggleMarkForReview(currentQuestion.id)}
                className="h-3.5 w-3.5 rounded text-amber-500 focus:ring-amber-400"
              />
              <span className="text-xs text-slate-500">Mark for review</span>
            </label>
          </div>

          {/* Prev / Next navigation */}
          <div className="flex gap-3">
            <button
              type="button"
              disabled={currentIndex === 0}
              onClick={() => setCurrentIndex((i) => i - 1)}
              className="btn-secondary flex-1 disabled:opacity-40"
            >
              Previous
            </button>
            {currentIndex < questions.length - 1 ? (
              <button
                type="button"
                disabled={!currentFullyAnswered}
                onClick={() => setCurrentIndex((i) => i + 1)}
                className="btn-primary flex-1 disabled:opacity-40"
                title={!currentFullyAnswered ? "Answer this question to continue" : undefined}
              >
                Next
              </button>
            ) : (
              <button
                type="button"
                disabled={!allAnswered}
                onClick={handleSubmitClick}
                className="btn-primary flex-1 disabled:opacity-40"
                title={!allAnswered ? "Answer all questions to submit" : undefined}
              >
                Submit
              </button>
            )}
          </div>

          {/* Submit button always visible when all answered */}
          {allAnswered && currentIndex < questions.length - 1 && (
            <button
              type="button"
              onClick={handleSubmitClick}
              className="btn-primary w-full mt-3"
            >
              Submit assessment
            </button>
          )}
        </div>

        {/* Right panel — navigator */}
        <aside className="w-56 shrink-0 border-l border-slate-200 bg-slate-50 px-4 py-6">
          <QuestionNavigator
            total={questions.length}
            currentIndex={currentIndex}
            answeredIds={answeredIds}
            markedIds={markedForReview}
            questions={questions}
            onJump={setCurrentIndex}
          />

          <div className="mt-6 pt-4 border-t border-slate-200">
            <p className="text-xs text-slate-500">
              <span className="font-semibold text-slate-700">{answeredIds.size}</span>
              {" "}of{" "}
              <span className="font-semibold text-slate-700">{questions.length}</span>
              {" "}answered
            </p>
          </div>
        </aside>
      </div>

      {/* Review overlay */}
      {showReview && (
        <ReviewOverview
          questions={questions}
          unansweredIds={unansweredIds}
          markedIds={markedForReview}
          onGoBack={() => setShowReview(false)}
          onConfirmSubmit={handleConfirmSubmit}
        />
      )}
    </div>
  );
}
