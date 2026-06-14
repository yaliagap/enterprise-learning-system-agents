/**
 * TypeScript types that mirror the backend Pydantic models exactly.
 * Field names match the actual Python models in workflow/state.py.
 */

export type QuestionType = "multiple_choice" | "multi_select" | "true_false";
export type Difficulty = "easy" | "medium" | "hard";
export type BloomLevel = "Remember" | "Understand" | "Apply" | "Analyze" | "Evaluate" | "Create";

export interface GroundingReference {
  title: string;
  url: string;
  type: string;
  score?: number | null;
}

/**
 * Public projection of AssessmentQuestion — correct_answers are stripped server-side.
 * explanation is included so we can show it in the results screen.
 */
export interface AssessmentQuestion {
  id: string;
  text: string;
  question_type: QuestionType;
  options: string[];
  correct_answer_count: number;
  domain: string;
  exam_weight_pct: number;
  explanation: string;
  difficulty: Difficulty;
  bloom_level: BloomLevel;
  is_scenario_based: boolean;
  scenario_context: string | null;
  grounding_reference: GroundingReference | null;
  // NOTE: correct_answers is intentionally absent — stripped by AssessmentQuestionPublic
}

export interface UserAnswer {
  question_id: string;
  selected_answers: string[];
}

export interface AssessmentAnswers {
  answers: UserAnswer[];
}

/**
 * Per-question scoring result returned by the backend after exam submission.
 * Field names match Python QuestionResult model exactly.
 */
export interface QuestionResult {
  question_id: string;
  user_answers: string[];       // plural — matches Python model (user_answers, not user_answer)
  correct_answers: string[];
  is_correct: boolean;
  partial_score: number;        // matches Python model (partial_score, not score_contribution)
  explanation: string;
}
