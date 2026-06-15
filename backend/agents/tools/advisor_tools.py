"""MAF @tool functions for the Certification Advisor agent."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from agent_framework import tool
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Return model
# ---------------------------------------------------------------------------


class TeamBenchmark(BaseModel):
    """Team benchmark data for a certification."""

    cert_id: str
    team_avg_score: float
    score_distribution: list[float] = Field(default_factory=list)
    team_domain_avgs: dict[str, float] = Field(default_factory=dict)
    sample_size: int = 0
    last_updated: str = ""
    has_data: bool = True


# ---------------------------------------------------------------------------
# Fixture loader (once at import time)
# ---------------------------------------------------------------------------

_BENCHMARK_PATH = (
    Path(__file__).parent.parent.parent / "data" / "fixtures" / "team_benchmark.json"
)


def _load_benchmarks() -> dict:
    try:
        return json.loads(_BENCHMARK_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


_BENCHMARKS = _load_benchmarks()


# ---------------------------------------------------------------------------
# Pure helper — available for executor to call deterministically
# ---------------------------------------------------------------------------


def percentile_rank(score: float, distribution: list[float]) -> int:
    """Return percentage of scores strictly below *score*. Empty list returns 50."""
    if not distribution:
        return 50
    below = sum(1 for s in distribution if s < score)
    return round(below / len(distribution) * 100)


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------


@tool
def get_team_benchmark(
    cert_id: Annotated[str, Field(description="Certification ID, e.g. 'AI-900', 'AI-102', 'AZ-900', 'AZ-104'.")],
) -> TeamBenchmark:
    """Return pre-computed team benchmark data for a certification.

    Reads from the internal team_benchmark.json fixture and returns team average score,
    score distribution, per-domain team averages, and sample size. Use this to compare
    the learner's score and domain performance against the rest of the team.

    Returns a TeamBenchmark with has_data=False and neutral defaults when the
    certification is not found in the fixture — never raises."""
    data = _BENCHMARKS.get(cert_id.upper(), {})
    if not data:
        return TeamBenchmark(
            cert_id=cert_id.upper(),
            team_avg_score=70.0,
            score_distribution=[],
            team_domain_avgs={},
            sample_size=0,
            last_updated="",
            has_data=False,
        )
    return TeamBenchmark(
        cert_id=cert_id.upper(),
        team_avg_score=data.get("team_avg_score", 70.0),
        score_distribution=data.get("score_distribution", []),
        team_domain_avgs=data.get("team_domain_avgs", {}),
        sample_size=data.get("sample_size", 0),
        last_updated=data.get("last_updated", ""),
        has_data=True,
    )
