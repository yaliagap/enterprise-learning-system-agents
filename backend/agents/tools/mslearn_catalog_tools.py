"""MAF @tool functions that call the Microsoft Learn Catalog API.

Call chain for the curator agent:
  1. search_azure_certifications(role?, level?)
       → returns cert list with UID, exam IDs, prerequisites
  2. search_learning_paths(exam_id)
       → resolves the cert → course → LP hierarchy from the Catalog API.
         Returns all self-paced LPs for the exam with per-LP duration and module count.
  3. get_learning_path(uid)
       → returns one LP with all modules and their exact durations
  4. get_module_details(uid)          [optional — max granularity]
       → returns one module with all units and per-unit duration

LP resolution strategy in search_learning_paths:
  Strategy 1 (primary): course-based 2-hop
    ?uid=course.{exam_slug}t00 → course.study_guide[] → LP UIDs
    Covers all certs that have a standard ILT course (az-900t00, ai-103t00, etc.)
  Strategy 2 (fallback): UID pattern match across full catalog
    Covers certs where the exam slug appears in LP UIDs (az-104, az-400, etc.)
  If both return empty → cert is retired or has no training published yet.

Reference: https://learn.microsoft.com/en-us/training/support/catalog-api-developer-reference
Base URL  : https://learn.microsoft.com/api/catalog/
"""
from __future__ import annotations

import logging
from typing import Annotated

import httpx
from agent_framework import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_BASE = "https://learn.microsoft.com/api/catalog/"
_TIMEOUT = 20.0


# ---------------------------------------------------------------------------
# Return models
# ---------------------------------------------------------------------------


class CertificationSummary(BaseModel):
    uid: str
    title: str
    levels: list[str]
    roles: list[str]
    prerequisites: list[str]   # prerequisite cert UIDs (e.g. must hold AZ-900 first)
    skills_measured: list[str] # high-level skill areas on the exam
    url: str


class SearchCertificationsResult(BaseModel):
    certifications: list[CertificationSummary]
    total: int


class LearningPathSummary(BaseModel):
    uid: str
    title: str
    duration_in_minutes: int
    estimated_hours: float
    module_count: int
    url: str


class SearchLearningPathsResult(BaseModel):
    exam_id: str
    learning_paths: list[LearningPathSummary]
    total_duration_in_minutes: int
    total_estimated_hours: float


class ModuleSummary(BaseModel):
    uid: str
    title: str
    duration_in_minutes: int
    estimated_hours: float
    url: str
    unit_count: int


class LearningPathDetails(BaseModel):
    uid: str
    title: str
    duration_in_minutes: int
    estimated_hours: float
    url: str
    modules: list[ModuleSummary]
    levels: list[str] = []
    products: list[str] = []
    icon_url: str = ""


class UnitSummary(BaseModel):
    uid: str
    title: str
    duration_in_minutes: int


class ModuleDetails(BaseModel):
    uid: str
    title: str
    duration_in_minutes: int
    estimated_hours: float
    url: str
    units: list[UnitSummary]


# ---------------------------------------------------------------------------
# Internal HTTP helper
# ---------------------------------------------------------------------------


async def _catalog_get(params: dict) -> dict:
    params.setdefault("locale", "en-us")
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(_BASE, params=params)
        resp.raise_for_status()
        return resp.json()


def _lp_to_summary(lp: dict) -> LearningPathSummary:
    dur = int(lp.get("duration_in_minutes") or 0)
    mod_uids = lp.get("modules") or []
    return LearningPathSummary(
        uid=lp["uid"],
        title=lp.get("title", ""),
        duration_in_minutes=dur,
        estimated_hours=round(dur / 60, 2),
        module_count=len(mod_uids),
        url=lp.get("url", ""),
    )


def _filter_educator(lps: list[dict]) -> list[dict]:
    return [
        lp for lp in lps
        if "prepare-teach" not in lp.get("uid", "").lower()
        and "educator" not in lp.get("uid", "").lower()
    ]


async def _resolve_lp_uids(uids: list[str], from_data: dict) -> list[dict]:
    """Return LP dicts for each UID, fetching any not present in from_data."""
    lps_by_uid: dict[str, dict] = {
        lp["uid"]: lp
        for lp in (from_data.get("learningPaths") or [])
        if lp.get("uid")
    }
    missing = [uid for uid in uids if uid not in lps_by_uid]
    if missing:
        try:
            batch = await _catalog_get({"learningPaths": " ".join(missing)})
            for lp in batch.get("learningPaths") or []:
                if lp.get("uid"):
                    lps_by_uid[lp["uid"]] = lp
        except Exception as exc:
            logger.warning("[mslearn] LP batch fetch failed: %s", exc)
    return [lps_by_uid[uid] for uid in uids if uid in lps_by_uid]


# ---------------------------------------------------------------------------
# Tool 1 — search_azure_certifications
# ---------------------------------------------------------------------------


@tool
async def search_azure_certifications(
    role: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Optional MS Learn role slug. Common values: 'administrator', 'developer', "
                "'ai-engineer', 'data-engineer', 'security-engineer', 'solution-architect', "
                "'devops-engineer', 'network-engineer'."
            ),
        ),
    ] = None,
    level: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional level: 'beginner', 'intermediate', or 'advanced'.",
        ),
    ] = None,
) -> SearchCertificationsResult:
    """List Azure certifications available in the Microsoft Learn catalog.

    Returns cert UIDs, titles, levels, roles, prerequisite cert UIDs, and the
    skills measured on the exam. Use the title or cert UID to infer the exam ID
    (e.g. 'AZ-104', 'AZ-900') and pass it to search_learning_paths.
    """
    params: dict = {"products": "azure"}
    if role:
        params["roles"] = role
    if level:
        params["levels"] = level

    try:
        data = await _catalog_get(params)
    except Exception as exc:
        logger.warning("[mslearn] search_azure_certifications failed: %s", exc)
        return SearchCertificationsResult(certifications=[], total=0)

    # mergedCertifications includes skills, prerequisites, providers — prefer it
    raw = data.get("mergedCertifications") or data.get("certifications") or []
    certs: list[CertificationSummary] = []

    for c in raw:
        uid = c.get("uid", "")
        if not uid:
            continue

        prereqs: list[str] = []
        for p in c.get("prerequisites") or []:
            prereqs.append(p if isinstance(p, str) else p.get("uid", ""))

        skills: list[str] = []
        for s in c.get("skills") or []:
            skills.append(s if isinstance(s, str) else s.get("text", ""))

        certs.append(
            CertificationSummary(
                uid=uid,
                title=c.get("title", ""),
                levels=c.get("levels") or [],
                roles=c.get("roles") or [],
                prerequisites=[p for p in prereqs if p],
                skills_measured=[s for s in skills if s],
                url=c.get("url", ""),
            )
        )

    return SearchCertificationsResult(certifications=certs, total=len(certs))


# ---------------------------------------------------------------------------
# Tool 2 — search_learning_paths
# ---------------------------------------------------------------------------


@tool
async def search_learning_paths(
    exam_id: Annotated[
        str,
        Field(
            description=(
                "The Microsoft exam ID to search learning paths for, e.g. 'AZ-104', 'AZ-900', "
                "'AI-103', 'DP-700', 'AZ-305', 'SC-900'. Case-insensitive."
            )
        ),
    ],
) -> SearchLearningPathsResult:
    """Find all self-paced learning paths for a Microsoft certification exam.

    Resolves the Certification → Course → Learning Path hierarchy from the
    MS Learn Catalog API. Each learning path includes exact duration_in_minutes
    and module_count. Pass each uid to get_learning_path for module-level detail.
    """
    exam_slug = exam_id.lower().replace(" ", "-")  # "AZ-104" → "az-104"
    matched: list[dict] = []

    # ------------------------------------------------------------------
    # Strategy 1: Course-based lookup (primary)
    # Derive ILT course UID → fetch course → extract LP UIDs from study_guide.
    # The standard MS Learn ILT course UID pattern is course.{exam_slug}t00.
    # This avoids scanning the full 885-LP catalog.
    # ------------------------------------------------------------------
    course_uid = f"course.{exam_slug}t00"
    try:
        data = await _catalog_get({"uid": course_uid})
        courses = data.get("courses") or []
        course = next((c for c in courses if c.get("uid") == course_uid), None)

        if course:
            study_guide = course.get("study_guide") or []
            lp_uids = [
                item["uid"]
                for item in study_guide
                if item.get("type") == "learningPath"
            ]
            if lp_uids:
                matched = _filter_educator(await _resolve_lp_uids(lp_uids, data))
                logger.info(
                    "[mslearn] search_learning_paths(%s): Strategy 1 (course %s) → %d LPs",
                    exam_id, course_uid, len(matched),
                )
        else:
            logger.debug("[mslearn] search_learning_paths(%s): course %s not found in catalog", exam_id, course_uid)

    except Exception as exc:
        logger.warning("[mslearn] search_learning_paths(%s) course lookup failed: %s", exam_id, exc)

    # ------------------------------------------------------------------
    # Strategy 2: UID pattern match across full catalog (fallback)
    # Handles certs where the exam slug appears directly in LP UIDs
    # (az-104, az-400, ai-300, dp-700, etc.) and certs with non-standard
    # course UIDs that Strategy 1 missed.
    # ------------------------------------------------------------------
    if not matched:
        try:
            full_data = await _catalog_get({"products": "azure"})
            all_lps: list[dict] = full_data.get("learningPaths") or []
            pattern_matched = _filter_educator([
                lp for lp in all_lps
                if exam_slug in lp.get("uid", "").lower()
            ])
            if pattern_matched:
                matched = pattern_matched
                logger.info(
                    "[mslearn] search_learning_paths(%s): Strategy 2 (UID pattern) → %d LPs",
                    exam_id, len(matched),
                )
            else:
                logger.info(
                    "[mslearn] search_learning_paths(%s): no LPs found — cert may be retired or training not yet published",
                    exam_id,
                )
        except Exception as exc:
            logger.warning("[mslearn] search_learning_paths(%s) full catalog fallback failed: %s", exam_id, exc)

    summaries = [_lp_to_summary(lp) for lp in matched]
    total_min = sum(s.duration_in_minutes for s in summaries)
    return SearchLearningPathsResult(
        exam_id=exam_id,
        learning_paths=summaries,
        total_duration_in_minutes=total_min,
        total_estimated_hours=round(total_min / 60, 2),
    )


# ---------------------------------------------------------------------------
# Tool 3 — get_learning_path
# ---------------------------------------------------------------------------


@tool
async def get_learning_path(
    uid: Annotated[
        str,
        Field(
            description=(
                "The learning path UID from search_learning_paths results, "
                "e.g. 'learn.az-104-manage-identities-governance'."
            )
        ),
    ],
) -> LearningPathDetails | None:
    """Return a learning path with all its modules and their exact durations.

    Each module has duration_in_minutes and estimated_hours — use these as the
    authoritative values for building the study schedule. Use module UIDs with
    get_module_details to see the individual unit breakdown.
    Returns None if the UID is not found.
    """
    try:
        data = await _catalog_get({"learningPaths": uid})
    except Exception as exc:
        logger.warning("[mslearn] get_learning_path(%s) failed: %s", uid, exc)
        return None

    lp_list = data.get("learningPaths") or []
    if not lp_list:
        return None

    lp = next((x for x in lp_list if x.get("uid") == uid), lp_list[0])
    module_uids: list[str] = lp.get("modules") or []

    modules_by_uid: dict[str, dict] = {
        m["uid"]: m for m in (data.get("modules") or []) if m.get("uid")
    }

    missing = [u for u in module_uids if u not in modules_by_uid]
    if missing:
        try:
            batch = await _catalog_get({"modules": " ".join(missing)})
            for m in batch.get("modules") or []:
                if m.get("uid"):
                    modules_by_uid[m["uid"]] = m
        except Exception as exc:
            logger.warning("[mslearn] module batch fetch failed: %s", exc)

    modules: list[ModuleSummary] = []
    for mod_uid in module_uids:
        m = modules_by_uid.get(mod_uid)
        if not m:
            continue
        dur = int(m.get("duration_in_minutes") or 0)
        modules.append(
            ModuleSummary(
                uid=mod_uid,
                title=m.get("title", ""),
                duration_in_minutes=dur,
                estimated_hours=round(dur / 60, 2),
                url=m.get("url", ""),
                unit_count=int(m.get("number_of_children") or len(m.get("units") or [])),
            )
        )

    lp_dur = int(lp.get("duration_in_minutes") or 0)
    return LearningPathDetails(
        uid=uid,
        title=lp.get("title", ""),
        duration_in_minutes=lp_dur,
        estimated_hours=round(lp_dur / 60, 2),
        url=lp.get("url", ""),
        modules=modules,
        levels=lp.get("levels") or [],
        products=lp.get("products") or [],
        icon_url=lp.get("icon_url") or "",
    )


# ---------------------------------------------------------------------------
# Tool 4 — get_module_details
# ---------------------------------------------------------------------------


@tool
async def get_module_details(
    uid: Annotated[
        str,
        Field(
            description=(
                "The module UID from a LearningPathDetails.modules list, "
                "e.g. 'learn.wwl.understand-azure-active-directory'."
            )
        ),
    ],
) -> ModuleDetails | None:
    """Return a module with all its units and their individual durations.

    Units are the finest MS Learn content granularity: typically 6-10 units per
    module ranging from 1 to 10 minutes each (introduction, topic units, knowledge
    check, summary). The module's duration_in_minutes equals the sum of its units.
    Returns None if the UID is not found.
    """
    try:
        data = await _catalog_get({"modules": uid})
    except Exception as exc:
        logger.warning("[mslearn] get_module_details(%s) failed: %s", uid, exc)
        return None

    mod_list = data.get("modules") or []
    if not mod_list:
        return None
    m = next((x for x in mod_list if x.get("uid") == uid), mod_list[0])

    unit_uids: list[str] = m.get("units") or []
    units_by_uid: dict[str, dict] = {
        u["uid"]: u for u in (data.get("units") or []) if u.get("uid")
    }

    missing = [u for u in unit_uids if u not in units_by_uid]
    if missing:
        try:
            batch = await _catalog_get({"units": " ".join(missing)})
            for u in batch.get("units") or []:
                if u.get("uid"):
                    units_by_uid[u["uid"]] = u
        except Exception as exc:
            logger.warning("[mslearn] unit batch fetch failed: %s", exc)

    units: list[UnitSummary] = []
    for unit_uid in unit_uids:
        u = units_by_uid.get(unit_uid)
        if not u:
            continue
        units.append(
            UnitSummary(
                uid=unit_uid,
                title=u.get("title", ""),
                duration_in_minutes=int(u.get("duration_in_minutes") or 0),
            )
        )

    dur = int(m.get("duration_in_minutes") or 0)
    return ModuleDetails(
        uid=uid,
        title=m.get("title", ""),
        duration_in_minutes=dur,
        estimated_hours=round(dur / 60, 2),
        url=m.get("url", ""),
        units=units,
    )
