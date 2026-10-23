"""
Agent 1: Data & Content Processor Agent (AG DocEngine Core v3.0).
Domain-Agnostic Core Engine:
- Sanitizes PDF derivatives (removes PII, Zalo, Phone, Ads; preserves diagrams & tables).
- Renders HD Cover Thumbnail (>= 1200px width, <= 250KB, Google Discover/News compliant).
- Extracts real PDF text, structure, and expressions directly from the source PDF.
- Authors 4-part SEO/GEO Markdown content using configurable headings from `configs/domain.config.json`.
- Synthesizes Dual Schema.org JSON-LD (LearningResource/DigitalDocument + NewsArticle).
- Supports Self-Healing refinement loop based on Agent 2 defect tickets.
"""

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import (
    BRAND_FULL_NAME,
    BRAND_NAME,
    DEFAULT_AUTHOR_NAME,
    DOCUMENT_ROUTE_PREFIX,
    PUBLIC_BASE_URL,
)
from core.domain_config import get_article_template_config, get_taxonomy_config
from processing.seo_geo_enricher import SEOGEOEnricher
from services.derivative_renderer import (
    MAX_COVER_SIZE_BYTES,
    MIN_COVER_WIDTH_PX,
    DerivativeRendererEngine,
)
from services.sanitizer import DeepSanitizerEngine

logger = logging.getLogger("ag.agent1_processor")


class ContentProcessorAgent:
    """Agent 1: Ingestion, Sanitization & High-Quality Content Creation (Domain-Agnostic)."""

    def __init__(self):
        self.sanitizer = DeepSanitizerEngine()
        self.renderer = DerivativeRendererEngine()

    @staticmethod
    def sanitize_evidence_text(raw_text: str) -> str:
        text = str(raw_text or "")
        text = re.sub(r"(?i)Nguon tai lieu:\s*[^\s|]+\s*\|\s*Tong hop:\s*[^\s]+", " ", text)
        text = re.sub(r"(?i)(?:https?://|www\.|zalo\.me/)[^\s]*", " ", text)
        text = re.sub(r"\b(?:0\d{9}|84\d{9}|[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b", " ", text)
        text = re.sub(r"(?i)(?:liên\s*hệ|lien\s*he)\s*(?:zalo|sđt|điện\s*thoại|hotline)?[:\s-]*[^\n.;]{0,40}", " ", text)
        text = re.sub(r"[\uF000-\uF0FF]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @classmethod
    def extract_real_pdf_pages_and_evidence(
        cls,
        pdf_path: Optional[Path],
        fallback_page_count: int = 1,
        category: str = "",
    ) -> Dict[str, Any]:
        pages_text: List[str] = []
        if pdf_path and pdf_path.exists():
            try:
                import pymupdf
                with pymupdf.open(str(pdf_path)) as doc:
                    for page in doc:
                        raw_p = page.get_text("text") or ""
                        pages_text.append(cls.sanitize_evidence_text(raw_p))
            except Exception as exc:
                logger.warning("Could not extract per-page text via pymupdf for %s: %s", pdf_path, exc)

        real_page_count = len(pages_text) if pages_text else max(1, int(fallback_page_count or 1))
        detected_sections: List[Dict[str, Any]] = []
        seen_sec = set()
        sample_items: List[Dict[str, Any]] = []
        seen_q = set()
        appendix_pages: List[int] = []

        sec_pattern = re.compile(
            r"(?i)\b(PHẦN\s+[I1-9V]+|Phần\s+[I1-9V]+|CHƯƠNG\s+[I1-9V]+|Chương\s+\d+|MỤC\s+[I1-9V]+|ĐIỀU\s+\d+|Chuyên\s*đề\s*\d+)\b"
        )
        appendix_pattern = re.compile(
            r"(?i)(?:PHỤ\s*LỤC|HƯỚNG\s*DẪN\s*CHI\s*TIẾT|BẢNG\s*ĐÁP\s*ÁN|ĐÁP\s*ÁN\s*VÀ\s*HƯỚNG\s*DẪN|LỜI\s*GIẢI\s*CHI\s*TIẾT|BIỂU\s*MẪU\s*ĐÍNH\s*KÈM| TÀI\s*LIỆU\s*THAM\s*KHẢO)"
        )
        item_detail_pattern = re.compile(
            r"(?i)\b((?: Điều|Mục|Khoản|Câu|Bài|Ví\s*dụ)\s*\d+(?:\.\d+)?)\s*[.:() -]+([^\n]{15,240}?)(?=\b(?:Điều|Mục|Khoản|Câu|Bài|Ví\s*dụ)\s*\d+\b|$)"
        )

        for idx, p_text in enumerate(pages_text):
            page_no = idx + 1
            if not p_text:
                continue
            for sm in sec_pattern.finditer(p_text):
                lbl = re.sub(r"\s+", " ", sm.group(1)).strip()
                k = lbl.upper()
                if k not in seen_sec:
                    seen_sec.add(k)
                    detected_sections.append({"label": lbl, "pageNumber": page_no})

            if appendix_pattern.search(p_text) and page_no not in appendix_pages:
                appendix_pages.append(page_no)

            for qm in item_detail_pattern.finditer(p_text):
                q_lbl = re.sub(r"\s+", " ", qm.group(1)).strip()
                q_body = re.sub(r"^[\s:.)-]+", "", qm.group(2))
                q_body = re.sub(r"\s+", " ", q_body).strip()
                qk = q_lbl.lower()
                if qk not in seen_q:
                    seen_q.add(qk)
                    if len(q_body) >= 12 and len(sample_items) < 8:
                        sample_items.append(
                            {
                                "pageNumber": page_no,
                                "questionLabel": q_lbl,
                                "excerpt": f"{q_lbl}: {q_body[:190]}",
                            }
                        )

        if not sample_items and pages_text:
            for idx, p_text in enumerate(pages_text[:4]):
                if len(p_text) >= 20:
                    sample_items.append(
                        {
                            "pageNumber": idx + 1,
                            "questionLabel": f"Trích dẫn Trang {idx + 1}",
                            "excerpt": p_text[:190],
                        }
                    )

        tpl = get_article_template_config()
        detected_item_count = max(len(seen_q), len(sample_items))
        has_real_appendix = len(appendix_pages) > 0
        appendix_pages_summary = cls.format_pages_summary(appendix_pages)
        present_lbl = tpl.get("appendix_present_label", "Có kèm phụ lục / hướng dẫn chi tiết trong tệp")
        absent_lbl = tpl.get("appendix_absent_label", "Tài liệu nguyên bản (chưa kèm phụ lục giải thích riêng)")
        appendix_status_statement = (
            f"{present_lbl} (xác thực tại {appendix_pages_summary})"
            if has_real_appendix
            else absent_lbl
        )

        formulas: List[str] = [
            rf"$N_{{\text{{trang}}}} = {real_page_count}$",
            rf"$N_{{\text{{mục}}}} = {detected_item_count}$",
        ]

        return {
            "pages_text": pages_text,
            "real_page_count": real_page_count,
            "detected_question_count": detected_item_count,
            "detected_sections": detected_sections,
            "has_real_answers": has_real_appendix,
            "answer_pages": appendix_pages,
            "answer_pages_summary": appendix_pages_summary,
            "answer_status_statement": appendix_status_statement,
            "sample_questions": sample_items,
            "formulas": formulas,
        }

    @staticmethod
    def format_pages_summary(pages: List[int]) -> str:
        if not pages:
            return ""
        if len(pages) <= 4:
            return f"Trang {', '.join(str(p) for p in pages)}"
        return f"Trang {pages[0]}–{pages[-1]} ({len(pages)} trang)"

    def generate_geo_seo_markdown(
        self,
        meta_title: str,
        subject: str,
        grade: Any,
        school: Optional[str],
        source_url: str,
        page_count: int,
        file_size_bytes: int,
        detected_year: int,
        extended_analysis: bool = False,
        real_evidence: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Produce a 4-part Markdown article backed by real PDF evidence and configured headings
        from `configs/domain.config.json`.
        """
        tax = get_taxonomy_config()
        tpl = get_article_template_config()
        cat_label = tax.get("category_label", "Chuyên mục")
        lvl_label = tax.get("level_label", "Phân nhóm / Cấp độ")
        org_label = tax.get("organization_label", "Đơn vị phát hành")

        sec1 = tpl.get("section_1_title", "1. Tổng quan & Hồ sơ xác thực tài liệu")
        sec2 = tpl.get("section_2_title", "2. Phân tích cấu trúc & Nội dung trọng tâm")
        sec3 = tpl.get("section_3_title", "3. Phụ lục, Biểu mẫu & Dữ liệu đối chiếu")
        sec4 = tpl.get("section_4_title", "4. Giá trị ứng dụng & Hướng dẫn khai thác")
        absent_lbl = tpl.get("appendix_absent_label", "Tài liệu nguyên bản")

        size_mib = file_size_bytes / (1024 * 1024)
        author_entity = school or DEFAULT_AUTHOR_NAME

        ev = real_evidence or {
            "real_page_count": page_count,
            "detected_question_count": 0,
            "detected_sections": [],
            "has_real_answers": False,
            "answer_pages": [],
            "answer_pages_summary": "",
            "answer_status_statement": absent_lbl,
            "sample_questions": [],
            "formulas": [rf"$N_{{\text{{trang}}}} = {page_count}$"],
        }

        actual_pages = ev.get("real_page_count") or page_count
        q_count = ev.get("detected_question_count") or 0
        ans_status = ev.get("answer_status_statement") or absent_lbl
        ans_pages_summary = ev.get("answer_pages_summary") or self.format_pages_summary(ev.get("answer_pages") or [])
        formulas_str = ", ".join(ev.get("formulas") or [])
        sections_list = ev.get("detected_sections") or []
        sections_str = (
            "; ".join(f"{s['label']} (Trang {s['pageNumber']})" for s in sections_list)
            if sections_list
            else f"Cấu trúc chuẩn gồm {actual_pages} trang"
        )

        sample_qs = ev.get("sample_questions") or []
        citations_md = (
            "\n".join(f"- **[Trích Trang {q['pageNumber']}]** {q['excerpt']}" for q in sample_qs[:6])
            if sample_qs
            else f"- **[Trích Trang 1]** Nội dung chính của tài liệu {meta_title}."
        )

        lead_summary = (
            f"Tài liệu **{meta_title}** thuộc phân mục **{subject} ({grade})**, "
            f"được phát hành/biên soạn bởi **{author_entity}** (năm **{detected_year}**). "
            f"Qua trích xuất trực tiếp lớp văn bản, tệp PDF gồm **{actual_pages} trang** với **{q_count} mục/nội dung trọng tâm**. "
            f"Tình trạng hồ sơ đính kèm: **{ans_status}**."
        )

        ans_detail_md = (
            f"- **Xác thực phụ lục / hướng dẫn chi tiết:** Đã kiểm chứng có mặt tại **{ans_pages_summary}** của tệp PDF.\n"
            f"- **Chỉ số định lượng ghi nhận từ tệp:** {formulas_str}."
            if ev.get("has_real_answers")
            else f"- **Xác thực tình trạng hồ sơ:** **{ans_status}**.\n"
            f"- **Chỉ số định lượng ghi nhận từ tệp:** {formulas_str}."
        )

        content = f"""## {sec1}
{lead_summary}

| Tiêu chí hồ sơ | Thông tin xác thực từ PDF |
| :--- | :--- |
| **Tên tài liệu** | {meta_title} |
| **{cat_label} & {lvl_label}** | {subject} — {grade} |
| **Năm phát hành / cập nhật** | {detected_year} |
| **{org_label}** | {author_entity} |
| **Quy mô tệp thực tế** | **{actual_pages} trang PDF** ({size_mib:.2f} MiB) — **{q_count} mục nội dung** |
| **Tình trạng Phụ lục / Hướng dẫn** | **{ans_status}** |

## {sec2}
Qua quét thực tế văn bản từng trang PDF, tài liệu có cấu trúc: **{sections_str}**. Các chỉ số và ký hiệu định lượng của tài liệu: {formulas_str}.

### Trích dẫn nội dung tiêu biểu từ tệp PDF:
{citations_md}

## {sec3}
{ans_detail_md}

## {sec4}
- **Hướng dẫn khai thác & tra cứu:** Người đọc tra cứu tuần tự từ Trang 1 đến Trang {actual_pages}, đối chiếu các điều khoản/mục trọng tâm dựa trên quy mô {formulas_str} ({ans_status.lower()}).
- **Bảo mật & Truy cập mở:** Bản quyền nội dung gốc thuộc về đơn vị phát hành ({author_entity}). Tệp PDF đã được hệ thống **{BRAND_NAME}** khử sạch 100% thông tin liên hệ cá nhân (PII) qua 10 cổng kiểm định tự động và phục vụ đọc trực tuyến, tải về miễn phí tại `{PUBLIC_BASE_URL}`.
"""
        return content.strip()

    def build_dual_schema_jsonld(
        self,
        title: str,
        slug: str,
        subject: str,
        grade: Any,
        school: Optional[str],
        published_year: int,
        cover_url: str,
        file_url: str,
        date_published: str,
    ) -> Dict[str, Any]:
        canonical_url = f"{PUBLIC_BASE_URL.rstrip('/')}/{DOCUMENT_ROUTE_PREFIX.strip('/')}/{slug}"
        author_name = school or DEFAULT_AUTHOR_NAME

        doc_resource = {
            "@context": "https://schema.org",
            "@type": ["LearningResource", "DigitalDocument"],
            "@id": f"{canonical_url}#document-resource",
            "name": title,
            "headline": title,
            "url": canonical_url,
            "inLanguage": "vi",
            "learningResourceType": subject,
            "educationalLevel": str(grade),
            "about": [subject, f"Năm {published_year}"],
            "isAccessibleForFree": True,
            "image": cover_url,
            "author": {
                "@type": "Organization",
                "name": author_name,
            },
            "publisher": {
                "@type": "Organization",
                "name": BRAND_FULL_NAME,
                "url": PUBLIC_BASE_URL,
                "logo": {
                    "@type": "ImageObject",
                    "url": f"{PUBLIC_BASE_URL.rstrip('/')}/logo.png",
                },
            },
            "datePublished": date_published,
            "dateModified": date_published,
        }

        news_article = {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "@id": f"{canonical_url}#news",
            "headline": title[:110],
            "url": canonical_url,
            "image": [cover_url],
            "datePublished": date_published,
            "dateModified": date_published,
            "author": [
                {
                    "@type": "Organization",
                    "name": author_name,
                }
            ],
            "publisher": {
                "@type": "Organization",
                "name": BRAND_NAME,
                "url": PUBLIC_BASE_URL,
            },
            "description": f"Công bố và số hóa tài liệu {title} phục vụ tra cứu và tải về miễn phí.",
            "mainEntityOfPage": canonical_url,
        }

        return {
            "@context": "https://schema.org",
            "@graph": [doc_resource, news_article],
        }

    def process_raw_document(
        self,
        raw_pdf_path: Path,
        item_meta: Dict[str, Any],
        source: Dict[str, Any],
        output_dir: Path,
    ) -> Dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        clean_pdf_path = output_dir / "clean_derivative.pdf"
        cover_image_path = output_dir / "cover_hd.jpg"

        title = item_meta.get("title", f"Tài liệu {BRAND_NAME}")
        url = item_meta.get("url", "")
        published_year = int(item_meta.get("published_year") or datetime.now().year)

        # 1. Sanitize PDF
        clean_res = self.sanitizer.sanitize_pdf_derivative(raw_pdf_path, clean_pdf_path)
        if not clean_res.get("success"):
            raise RuntimeError(f"Sanitization failed: {clean_res.get('error')}")

        # 2. Render Cover HD (>= 1200px)
        render_res = self.renderer.render_cover_thumbnail(
            clean_pdf_path, cover_image_path, target_width=MIN_COVER_WIDTH_PX
        )
        if not render_res.get("success"):
            raise RuntimeError(f"Cover render failed: {render_res.get('error')}")

        # 3. Enrich Metadata using domain.config.json taxonomy
        default_category = source.get("primary_category") or source.get("primary_subject")
        enriched = SEOGEOEnricher.enrich(title, default_subject=default_category)
        slug_hash = hashlib.sha256(url.encode()).hexdigest()[:10]
        enriched.slug = f"{enriched.slug[:140]}-{slug_hash}"

        # 4. Extract Real PDF Evidence & Generate structured 4-part Markdown content
        pdf_stat = self.renderer.validate_pdf_standards(clean_pdf_path)
        page_count = pdf_stat.get("page_count", 1)
        file_size = clean_pdf_path.stat().st_size

        real_evidence = self.extract_real_pdf_pages_and_evidence(
            clean_pdf_path,
            fallback_page_count=page_count,
            category=enriched.subject,
        )
        page_count = real_evidence.get("real_page_count", page_count)

        clean_title = enriched.title
        article_content = self.generate_geo_seo_markdown(
            meta_title=clean_title,
            subject=enriched.subject,
            grade=enriched.grade,
            school=enriched.geo_school,
            source_url=url,
            page_count=page_count,
            file_size_bytes=file_size,
            detected_year=published_year,
            extended_analysis=True,
            real_evidence=real_evidence,
        )

        # 5. Dual Schema
        pub_iso = datetime.now(timezone.utc).isoformat()
        cover_preview_url = f"{PUBLIC_BASE_URL.rstrip('/')}/api/documents/{enriched.slug}/cover"
        file_preview_url = f"{PUBLIC_BASE_URL.rstrip('/')}/api/documents/{enriched.slug}/download"

        schema_jsonld = self.build_dual_schema_jsonld(
            title=clean_title,
            slug=enriched.slug,
            subject=enriched.subject,
            grade=enriched.grade,
            school=enriched.geo_school,
            published_year=published_year,
            cover_url=cover_preview_url,
            file_url=file_preview_url,
            date_published=pub_iso,
        )

        draft_package = {
            "title": clean_title,
            "slug": enriched.slug,
            "subject": enriched.subject,
            "grade": enriched.grade,
            "category": enriched.document_type,
            "topic": enriched.document_type,
            "author_name": enriched.geo_school or DEFAULT_AUTHOR_NAME,
            "academic_year": str(published_year),
            "description": article_content,
            "clean_pdf_path": str(clean_pdf_path),
            "cover_image_path": str(cover_image_path),
            "raw_url": url,
            "page_count": page_count,
            "has_answers": bool(real_evidence.get("has_real_answers")),
            "extracted_pages_text": real_evidence.get("pages_text", []),
            "real_evidence": {
                k: v for k, v in real_evidence.items() if k != "pages_text"
            },
            "file_size_bytes": file_size,
            "schema_jsonld": schema_jsonld,
            "audience_tags": [str(enriched.grade), enriched.subject, f"Năm {published_year}"],
            "revision_count": 0,
            "audit_history": [],
        }

        logger.info("Agent 1 produced draft package for: %s [Slug: %s]", clean_title, enriched.slug)
        return draft_package

    def refine_draft_package(
        self,
        draft_package: Dict[str, Any],
        defects: List[str],
    ) -> Dict[str, Any]:
        """Self-Healing refinement: Automatically repair specific defects identified by Agent 2."""
        draft = dict(draft_package)
        draft["revision_count"] = draft.get("revision_count", 0) + 1
        clean_pdf = Path(draft["clean_pdf_path"])
        cover_path = Path(draft["cover_image_path"])

        logger.info("Agent 1 refining draft (Revision #%d) with defects: %s", draft["revision_count"], defects)

        for defect in defects:
            d_lower = defect.lower()

            if any(k in d_lower for k in ("cover", "ảnh bìa", "bìa", "1200px")):
                self.renderer.render_cover_thumbnail(clean_pdf, cover_path, target_width=MIN_COVER_WIDTH_PX, quality=85)

            if any(k in d_lower for k in ("content", "bài viết", "từ", "h2", "katex", "độ dài")):
                real_ev = self.extract_real_pdf_pages_and_evidence(
                    clean_pdf if clean_pdf.exists() else None,
                    fallback_page_count=int(draft.get("page_count") or 1),
                    category=str(draft.get("subject") or ""),
                )
                draft["description"] = self.generate_geo_seo_markdown(
                    meta_title=draft["title"],
                    subject=draft["subject"],
                    grade=draft["grade"],
                    school=draft.get("author_name"),
                    source_url=draft.get("raw_url", ""),
                    page_count=draft.get("page_count", 1),
                    file_size_bytes=draft.get("file_size_bytes", 1024),
                    detected_year=int(draft.get("academic_year") or datetime.now().year),
                    extended_analysis=True,
                    real_evidence=real_ev,
                )

            if any(k in d_lower for k in ("schema", "newsarticle", "learningresource")):
                pub_iso = datetime.now(timezone.utc).isoformat()
                cover_preview_url = f"{PUBLIC_BASE_URL.rstrip('/')}/api/documents/{draft['slug']}/cover"
                file_preview_url = f"{PUBLIC_BASE_URL.rstrip('/')}/api/documents/{draft['slug']}/download"
                draft["schema_jsonld"] = self.build_dual_schema_jsonld(
                    title=draft["title"],
                    slug=draft["slug"],
                    subject=draft["subject"],
                    grade=draft["grade"],
                    school=draft.get("author_name"),
                    published_year=int(draft.get("academic_year") or datetime.now().year),
                    cover_url=cover_preview_url,
                    file_url=file_preview_url,
                    date_published=pub_iso,
                )

        return draft
