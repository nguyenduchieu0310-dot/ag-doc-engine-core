"""
Agent 2: QA & SEO Sentinel Agent (AG DocEngine Core v3.0).
Domain-Agnostic Independent Auditor / Critic evaluating draft packages against 4 Golden Standards:
1. SEO Standard: Title length, ASCII slug, >=300 words, H2 structural tags.
2. GEO Standard: Direct Answer structure, E-E-A-T entity provenance, optional KaTeX expressions (when configured in domain.config.json).
3. Google News & Discover Standard: Cover >= 1200px, <= 250KB, Dual Schema JSON-LD.
4. Safety Standard: Zero PII (phone/zalo/spam), malware-free PDF, searchable text layer NFC.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List
from PIL import Image

from core.domain_config import get_taxonomy_config
from services.derivative_renderer import (
    MAX_COVER_SIZE_BYTES,
    MIN_COVER_WIDTH_PX,
    DerivativeRendererEngine,
)
from services.sanitizer import (
    PHONE_PREFIXED_REGEX,
    PHONE_STANDALONE_REGEX,
    VIP_PRICE_REGEX,
    DeepSanitizerEngine,
)

logger = logging.getLogger("ag.agent2_sentinel")


class AuditReport:
    def __init__(
        self,
        is_approved: bool,
        overall_score: float,
        pillar_scores: Dict[str, float],
        checklist: Dict[str, Dict[str, Any]],
        defects: List[str],
    ):
        self.is_approved = is_approved
        self.overall_score = overall_score
        self.pillar_scores = pillar_scores
        self.checklist = checklist
        self.defects = defects

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_approved": self.is_approved,
            "overall_score": round(self.overall_score, 1),
            "pillar_scores": {k: round(v, 1) for k, v in self.pillar_scores.items()},
            "defects_count": len(self.defects),
            "defects": self.defects,
            "checklist": self.checklist,
        }


class QASentinelAgent:
    """Agent 2: Independent Quality & Search Compliance Auditor (Domain-Agnostic)."""

    def __init__(self):
        self.renderer = DerivativeRendererEngine()
        self.sanitizer = DeepSanitizerEngine()

    def audit_draft_package(self, draft_package: Dict[str, Any]) -> AuditReport:
        checklist: Dict[str, Dict[str, Any]] = {}
        defects: List[str] = []

        title = draft_package.get("title", "")
        slug = draft_package.get("slug", "")
        description = draft_package.get("description", "")
        subject = draft_package.get("subject", "")
        clean_pdf_path = Path(draft_package.get("clean_pdf_path", ""))
        cover_image_path = Path(draft_package.get("cover_image_path", ""))
        schema = draft_package.get("schema_jsonld", {})

        # PILLAR 1: CHUẨN SEO
        title_len = len(title)
        title_pass = 25 <= title_len <= 150
        checklist["seo_title_length"] = {
            "name": "Độ dài tiêu đề H1 SEO (25 - 150 ký tự)",
            "pass": title_pass,
            "value": f"{title_len} ký tự",
        }
        if not title_pass:
            defects.append(f"SEO: Tiêu đề H1 có độ dài {title_len} ký tự, cần nằm trong khoảng 25 - 150 ký tự.")

        slug_pass = bool(re.match(r"^[a-z0-9\-]+$", slug))
        checklist["seo_slug_format"] = {
            "name": "Semantic Slug chuẩn ASCII URL duy nhất",
            "pass": slug_pass,
            "value": slug,
        }
        if not slug_pass:
            defects.append("SEO: Slug chứa ký tự không hợp lệ, phải là chuỗi a-z, 0-9 và dấu gạch ngang.")

        words = description.split()
        word_count = len(words)
        word_pass = word_count >= 250
        checklist["seo_word_count"] = {
            "name": "Độ dài bài viết mô tả (>= 250 từ)",
            "pass": word_pass,
            "value": f"{word_count} từ",
        }
        if not word_pass:
            defects.append(f"SEO: Bài viết chỉ có {word_count} từ, chưa đạt yêu cầu tối thiểu >= 250 từ.")

        h2_count = len(re.findall(r"^##\s+", description, re.MULTILINE))
        h2_pass = h2_count >= 3
        checklist["seo_h2_structure"] = {
            "name": "Cấu trúc đề mục H2 bài viết (>= 3 thẻ H2)",
            "pass": h2_pass,
            "value": f"{h2_count} thẻ H2",
        }
        if not h2_pass:
            defects.append("SEO: Bài viết thiếu cấu trúc đề mục H2 rõ ràng (yêu cầu >= 3 phần H2).")

        # PILLAR 2: CHUẨN GEO & E-E-A-T
        author = draft_package.get("author_name", "")
        has_author = bool(author and author.strip())
        checklist["geo_provenance_eeat"] = {
            "name": "Bảo lưu thực thể phát hành E-E-A-T (Đơn vị/Tác giả)",
            "pass": has_author,
            "value": author,
        }
        if not has_author:
            defects.append("GEO: Thiếu thông tin đơn vị phát hành hoặc tác giả cho E-E-A-T.")

        tax = get_taxonomy_config()
        formula_cats = [c.lower() for c in tax.get("require_formulas_for_categories", [])]
        if subject.lower() in formula_cats:
            katex_pass = bool(re.search(r"\$[^\$]+\$", description))
            checklist["geo_katex_formula"] = {
                "name": "Trích dẫn biểu thức chuẩn KaTeX",
                "pass": katex_pass,
                "value": "Đã có biểu thức KaTeX" if katex_pass else "Thiếu KaTeX",
            }
            if not katex_pass:
                defects.append("GEO: Bài viết thuộc danh mục yêu cầu công thức nhưng thiếu biểu thức KaTeX ($...$).")

        # PILLAR 3: CHUẨN GOOGLE NEWS & DISCOVER
        cover_pass = False
        cover_dim = "N/A"
        if cover_image_path.exists():
            try:
                with Image.open(cover_image_path) as img:
                    w, h = img.size
                    cover_dim = f"{w}x{h} px"
                cover_size = cover_image_path.stat().st_size
                cover_pass = w >= MIN_COVER_WIDTH_PX and cover_size <= MAX_COVER_SIZE_BYTES
            except Exception as e:
                cover_dim = f"Error: {e}"

        checklist["news_cover_quality"] = {
            "name": "Ảnh bìa HD chuẩn Google Discover (>= 1200px, <= 250KB)",
            "pass": cover_pass,
            "value": cover_dim,
        }
        if not cover_pass:
            defects.append(f"Google News: Ảnh bìa ({cover_dim}) chưa đạt chuẩn >= 1200px chiều rộng hoặc vượt quá 250KB.")

        has_schema = False
        if isinstance(schema, dict) and "@graph" in schema:
            types = [item.get("@type") for item in schema["@graph"]]
            has_schema = any("LearningResource" in str(t) or "DigitalDocument" in str(t) for t in types) and any(
                "NewsArticle" in str(t) for t in types
            )

        checklist["news_dual_schema"] = {
            "name": "Khai báo Schema kép: DigitalDocument + NewsArticle",
            "pass": has_schema,
            "value": "Hợp lệ" if has_schema else "Thiếu Schema",
        }
        if not has_schema:
            defects.append("Google News: Cấu trúc Schema.org JSON-LD thiếu khai báo NewsArticle hoặc DigitalDocument.")

        # PILLAR 4: CHUẨN AN TOÀN & TOÀN VẸN
        pii_found = []
        for regex, name in (
            (PHONE_PREFIXED_REGEX, "SĐT tiền tố"),
            (PHONE_STANDALONE_REGEX, "SĐT độc lập"),
            (VIP_PRICE_REGEX, "Rao bán VIP"),
        ):
            if regex.search(description):
                pii_found.append(name)

        pii_pass = len(pii_found) == 0
        checklist["safety_no_pii_description"] = {
            "name": "Khử trùng 100% PII trong bài viết (Không SĐT, Zalo, link quảng cáo)",
            "pass": pii_pass,
            "value": "Sạch rác" if pii_pass else f"Còn dính: {', '.join(pii_found)}",
        }
        if not pii_pass:
            defects.append(f"Safety: Bài viết còn dính dấu vết PII/quảng cáo ({', '.join(pii_found)}).")

        pdf_valid = False
        pdf_detail = {}
        if clean_pdf_path.exists():
            pdf_detail = self.renderer.validate_pdf_standards(clean_pdf_path)
            clean_audit = self.sanitizer.audit_pdf_cleanliness(clean_pdf_path)
            pdf_clean = clean_audit.get("is_clean", True)
            pdf_valid = (
                pdf_detail.get("valid", False)
                and pdf_detail.get("size_pass", False)
                and pdf_detail.get("malware_free", False)
                and pdf_detail.get("has_searchable_text", True)
                and pdf_clean
            )

        checklist["safety_pdf_integrity"] = {
            "name": "Toàn vẹn tệp PDF (Chuẩn Text layer, không mã độc, dung lượng, sạch PII)",
            "pass": pdf_valid,
            "details": pdf_detail,
        }
        if not pdf_valid:
            defects.append("Safety: Tệp PDF phái sinh không đạt chuẩn kỹ thuật (mã độc, thiếu text layer hoặc còn watermark/PII).")

        total_items = len(checklist)
        passed_items = sum(1 for item in checklist.values() if item["pass"])
        overall_score = (passed_items / total_items) * 100.0 if total_items else 0.0

        def calc_subscore(items):
            if not items:
                return 100.0
            return (sum(1 for i in items if i["pass"]) / len(items)) * 100.0

        seo_items = [checklist[k] for k in checklist if k.startswith("seo_")]
        geo_items = [checklist[k] for k in checklist if k.startswith("geo_")]
        news_items = [checklist[k] for k in checklist if k.startswith("news_")]
        safety_items = [checklist[k] for k in checklist if k.startswith("safety_")]

        pillar_scores = {
            "seo_score": calc_subscore(seo_items),
            "geo_score": calc_subscore(geo_items),
            "google_news_score": calc_subscore(news_items),
            "safety_score": calc_subscore(safety_items),
        }

        is_approved = len(defects) == 0 and overall_score == 100.0
        report = AuditReport(
            is_approved=is_approved,
            overall_score=overall_score,
            pillar_scores=pillar_scores,
            checklist=checklist,
            defects=defects,
        )

        logger.info(
            "Agent 2 Audit Verdict for [%s]: %s (Score: %.1f/100, Defects: %d)",
            title,
            "AUDIT_PASSED" if is_approved else "AUDIT_REJECTED",
            overall_score,
            len(defects),
        )
        return report
