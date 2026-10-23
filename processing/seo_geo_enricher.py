import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.config import BRAND_NAME, PUBLIC_BASE_URL
from core.domain_config import get_taxonomy_config


def remove_accents(s: str) -> str:
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    res = "".join(c for c in nfkd if not unicodedata.combining(c))
    return res.replace("đ", "d").replace("Đ", "D")


def extract_geo_and_metadata(title: str, categories=None) -> Dict[str, Any]:
    """Generic entity & organization extractor (domain-agnostic)."""
    org_match = re.search(
        r"(?i)\b((?:Bộ|Sở|Phòng|Trường|Viện|Cục|Ủy\s*ban|Hiệp\s*hội|Tập\s*đoàn|Công\s*ty|THPT|THCS|Đại\s*học)\s+[^\n,;|()–-]{3,45})",
        title or "",
    )
    organization = org_match.group(1).strip() if org_match else None
    return {
        "geo_province": None,
        "geo_school": organization,
        "geo_region": None,
        "geo_evidence": [organization] if organization else [],
        "metadata_review_status": "verified" if organization else "needs_review",
    }


@dataclass
class EnrichedMetadata:
    title: str
    slug: str
    description: str
    subject: str
    grade: str
    academic_year: str
    geo_province: Optional[str]
    geo_school: Optional[str]
    curriculum: str
    document_type: str


class SEOGEOEnricher:
    """
    Domain-agnostic metadata enricher.
    Reads categories, levels, document types, and frameworks dynamically from `configs/domain.config.json`.
    """

    @classmethod
    def generate_slug(cls, title: str) -> str:
        clean_text = remove_accents(title).lower()
        slug = re.sub(r"[^a-z0-9]+", "-", clean_text).strip("-")
        return slug[:120] if slug else "tai-lieu-so"

    @classmethod
    def enrich(
        cls,
        title: str,
        default_subject: Optional[str] = None,
        raw_metadata: Optional[Dict[str, Any]] = None,
    ) -> EnrichedMetadata:
        tax = get_taxonomy_config()
        title_clean = title.strip()
        lower_title = title_clean.lower()

        # 1. Extract Organization / Provenance Entity
        geo_info = extract_geo_and_metadata(title_clean)
        province = geo_info.get("geo_province")
        organization = geo_info.get("geo_school")

        # 2. Extract Category (from domain.config.json taxonomy.categories)
        detected_category = default_subject or tax.get("default_category", "Tài liệu chuyên ngành")
        for item in tax.get("categories", []):
            cat_name = item.get("name", "")
            keywords = [k.lower() for k in item.get("keywords", [])]
            if any(k in lower_title for k in keywords):
                detected_category = cat_name
                break

        # 3. Extract Level / Audience Group (from domain.config.json taxonomy.levels)
        detected_level = tax.get("default_level", "Tiêu chuẩn")
        for item in tax.get("levels", []):
            lvl_name = item.get("name", "")
            keywords = [k.lower() for k in item.get("keywords", [])]
            if any(k in lower_title for k in keywords):
                detected_level = lvl_name
                break

        # 4. Extract Publication Year / Period
        pub_period = "2025-2026"
        year_match = re.search(r"\b(202[2-9]\s*[-–/]\s*202[3-9])\b", title_clean)
        if year_match:
            pub_period = re.sub(r"\s*[-–/]\s*", "-", year_match.group(1))
        else:
            single_year = re.search(r"\b(202[3-9])\b", title_clean)
            if single_year:
                pub_period = single_year.group(1)

        # 5. Extract Framework / Standard (from domain.config.json taxonomy.frameworks)
        framework = tax.get("default_framework", "Chuẩn Hiện hành")
        for item in tax.get("frameworks", []):
            fw_name = item.get("name", "")
            keywords = [k.lower() for k in item.get("keywords", [])]
            if any(k in lower_title for k in keywords):
                framework = fw_name
                break

        # 6. Extract Document Type (from domain.config.json taxonomy.document_types)
        doc_type = tax.get("default_document_type", "Tài liệu chuyên đề")
        for item in tax.get("document_types", []):
            dt_name = item.get("name", "")
            keywords = [k.lower() for k in item.get("keywords", [])]
            if any(k in lower_title for k in keywords):
                doc_type = dt_name
                break

        # 7. Generate Slug
        slug = cls.generate_slug(title_clean)

        # 8. Compose SEO Description
        org_text = f" do {organization} phát hành" if organization else ""
        description = (
            f"Tài liệu {title_clean}{org_text}. "
            f"Phân mục {detected_category} ({detected_level}) theo {framework}, "
            f"cập nhật {pub_period}, hỗ trợ đọc trực tuyến và tải file PDF miễn phí tại {BRAND_NAME} ({PUBLIC_BASE_URL})."
        )

        return EnrichedMetadata(
            title=title_clean,
            slug=slug,
            description=description,
            subject=detected_category,
            grade=detected_level,
            academic_year=pub_period,
            geo_province=province,
            geo_school=organization,
            curriculum=framework,
            document_type=doc_type,
        )
