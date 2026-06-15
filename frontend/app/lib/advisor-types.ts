// TypeScript interfaces mirroring the AdvisorResult Pydantic model from backend/workflow/state.py

export type PatternType = "conceptual_gap" | "application_gap" | "scenario_gap" | "bloom_gap" | "none";
export type TeamSignal = "individual_gap" | "shared_team_gap" | "on_par" | "ahead";
export type AdvisorScenario = "passed" | "max_retries";

export interface AdvisorScoreSummary {
  score: number;
  passed: boolean;
  passing_score: number;
  attempt: number;
}

export interface AdvisorPerformanceSnapshot {
  total_questions: number;
  correct: number;
  conceptual_correct_pct: number;
  application_correct_pct: number;
  scenario_correct_pct: number;
  has_scenario_gap: boolean;
  bloom_level_gap: PatternType;
}

export interface AdvisorTeamBenchmark {
  team_avg_score: number;
  team_percentile: number;
  comparison: string;
  team_signal: TeamSignal;
  sample_size: number;
  has_data: boolean;
}

export interface AdvisorDomainAnalysis {
  domain_name: string;
  learner_score: number;
  team_avg: number | null;
  delta_vs_team: number | null;
  pattern_type: PatternType;
  team_signal: TeamSignal;
}

export interface AdvisorStrongArea {
  domain_name: string;
  learner_score: number;
  note: string;
}

export interface AdvisorReviewArea {
  domain_name: string;
  learner_score: number;
  pattern_type: PatternType;
  note: string;
  resource_hint: string;
}

export interface AdvisorRetryComparison {
  first_attempt_score: number;
  last_attempt_score: number;
  delta: number;
  improved_domains: string[];
  regressed_domains: string[];
  summary: string;
}

export interface AdvisorRecommendation {
  order: number;
  title: string;
  detail: string;
  resource_hint: string;
}

export interface AdvisorResult {
  scenario: AdvisorScenario;
  cert_id: string;
  cert_name: string;
  official_cert_url: string;
  next_cert_suggestion: string;
  score_summary: AdvisorScoreSummary;
  performance_snapshot: AdvisorPerformanceSnapshot;
  team_benchmark: AdvisorTeamBenchmark;
  domain_analysis: AdvisorDomainAnalysis[];
  strong_areas: AdvisorStrongArea[];
  areas_to_review: AdvisorReviewArea[];
  retry_comparison: AdvisorRetryComparison | null;
  recommendations: AdvisorRecommendation[];
  closing_note: string;
}
