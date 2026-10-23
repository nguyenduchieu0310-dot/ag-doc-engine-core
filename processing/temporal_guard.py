import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from core.config import MIN_ELIGIBLE_YEAR
from core.domain_config import get_temporal_policy


def get_modern_keywords() -> List[str]:
    policy = get_temporal_policy()
    return [k.lower() for k in policy.get("always_accept_keywords", ["mới nhất", "cập nhật"])]


NEW_CURRICULUM_KEYWORDS: List[str] = get_modern_keywords()

VALID_ACADEMIC_YEARS_REGEX = re.compile(
    r"\b(?:202[3-9]|203\d|2022\s*[-–/]\s*2023|2023\s*[-–/]\s*2024|2024\s*[-–/]\s*2025|2025\s*[-–/]\s*2026|2026\s*[-–/]\s*2027)\b",
    re.IGNORECASE,
)

OLD_ACADEMIC_YEARS_REGEX = re.compile(
    r"\b(?:201\d|202[0-2]|2021\s*[-–/]\s*2022|2020\s*[-–/]\s*2021)\b",
    re.IGNORECASE,
)

OLD_URL_SLUG_REGEX = re.compile(
    r"(?:/(?:201\d|2020|2021|2022)/|-nam-2022\.html|-nam-2021\.html|-nam-2020\.html)",
    re.IGNORECASE,
)


@dataclass
class TemporalEvaluationResult:
    is_eligible: bool
    reason: str
    detected_year: Optional[int] = None
    curriculum: Optional[str] = None


class TemporalYearGuard:
    """
    Enforces publication year filtering (>= min_eligible_year from domain.config.json).
    Rejects outdated documents older than min_eligible_year.
    """

    @classmethod
    def evaluate(
        cls,
        title: str = "",
        url: str = "",
        published_at: Optional[str] = None,
        published_year: Optional[int] = None,
        content_preview: str = "",
    ) -> TemporalEvaluationResult:
        policy = get_temporal_policy()
        min_year = int(policy.get("min_eligible_year", MIN_ELIGIBLE_YEAR))
        combined_text = f"{title} {content_preview}".lower()

        # 1. Check always-accept keywords from domain.config.json
        for kw in get_modern_keywords():
            if kw and kw in combined_text:
                return TemporalEvaluationResult(
                    is_eligible=True,
                    reason="ACCEPTED_DOMAIN_PRIORITY_KEYWORD",
                    detected_year=published_year or datetime.now().year,
                    curriculum=kw.title(),
                )

        # 2. Check System Published Date
        if published_year is not None:
            if published_year < min_year:
                return TemporalEvaluationResult(
                    is_eligible=False,
                    reason="SKIPPED_OLD_PUBDATE",
                    detected_year=published_year,
                )
            return TemporalEvaluationResult(
                is_eligible=True,
                reason="ACCEPTED_PUBDATE_GE_MIN_YEAR",
                detected_year=published_year,
            )

        if published_at:
            try:
                dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                if dt.year < min_year:
                    return TemporalEvaluationResult(
                        is_eligible=False,
                        reason="SKIPPED_OLD_PUBDATE",
                        detected_year=dt.year,
                    )
                return TemporalEvaluationResult(
                    is_eligible=True,
                    reason="ACCEPTED_PUBDATE_GE_MIN_YEAR",
                    detected_year=dt.year,
                )
            except Exception:
                pass

        # 3. Check Old URL Slugs
        if url and OLD_URL_SLUG_REGEX.search(url):
            return TemporalEvaluationResult(
                is_eligible=False,
                reason="SKIPPED_OLD_URL_SLUG",
            )

        # 4. Check Year in Title
        valid_match = VALID_ACADEMIC_YEARS_REGEX.search(title)
        old_match = OLD_ACADEMIC_YEARS_REGEX.search(title)

        if valid_match and not old_match:
            year_str = valid_match.group(0)
            year_int = int(re.search(r"\d{4}", year_str).group(0))
            if year_int >= min_year:
                return TemporalEvaluationResult(
                    is_eligible=True,
                    reason="ACCEPTED_YEAR_REGEX",
                    detected_year=year_int,
                )

        if old_match and not valid_match:
            year_str = old_match.group(0)
            year_int = int(re.search(r"\d{4}", year_str).group(0))
            return TemporalEvaluationResult(
                is_eligible=False,
                reason="SKIPPED_OLD_YEAR",
                detected_year=year_int,
            )

        for year in range(2028, min_year - 1, -1):
            if str(year) in title:
                return TemporalEvaluationResult(
                    is_eligible=True,
                    reason=f"ACCEPTED_YEAR_IN_TITLE_{year}",
                    detected_year=year,
                )

        return TemporalEvaluationResult(
            is_eligible=False,
            reason="SKIPPED_NO_ELIGIBLE_YEAR_FOUND",
        )
