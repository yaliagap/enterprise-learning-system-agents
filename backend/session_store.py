"""In-process session store shared between server.py and workflow dispatcher.

Keyed by learner_id. Holds data that must survive across separate AG-UI
invocations within the same FastAPI process lifetime (e.g. full assessment
questions with correct answers, selected module IDs).
"""

from typing import Any

_sessions: dict[str, dict[str, Any]] = {}


def get(learner_id: str) -> dict[str, Any]:
    return _sessions.get(learner_id, {})


def set_key(learner_id: str, key: str, value: Any) -> None:
    if learner_id not in _sessions:
        _sessions[learner_id] = {}
    _sessions[learner_id][key] = value


def merge(learner_id: str, overrides: dict[str, Any]) -> None:
    if learner_id not in _sessions:
        _sessions[learner_id] = {}
    _sessions[learner_id].update(overrides)
