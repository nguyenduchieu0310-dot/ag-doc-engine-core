import logging
import re
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlparse
import pymupdf

from core.config import BRAND_NAME, PUBLIC_BASE_URL

logger = logging.getLogger("ag_doc_engine.watermark")

DE_WATERMARK_PATTERNS = [
    re.compile(r'(?i)(?:https?://)?(?:www\.)?[a-z0-9\-]{4,}\.(?:com|vn|net|edu\.vn|org)(?:/[^\s]*)?'),
    re.compile(r'(?i)(?:hotline|zalo|liên hệ|fanpage|sđt|đt)\s*[:.]?\s*(?:09\d|08\d|07\d|03\d)[\d.\s]{7,10}'),
    re.compile(r'(?i)nhóm\s+(?:vip|zalo|chia sẻ tài liệu|hỗ trợ)'),
    re.compile(r'(?i)sưu\s+tầm\s+và\s+biên\s+soạn'),
]

# Colors: Light Slate Gray (#CBD5E1) and Slate (#64748B)
WATERMARK_COLOR = (203 / 255.0, 213 / 255.0, 225 / 255.0)
FOOTER_COLOR = (100 / 255.0, 116 / 255.0, 139 / 255.0)


def _portal_host() -> str:
    parsed = urlparse(PUBLIC_BASE_URL)
    return parsed.netloc or BRAND_NAME


class SmartWatermarkEngine:
    """
    Cleans unwanted third-party noisy annotations/domains and applies subtle portal underlay branding.
    Maintains 100% legibility of document text, equations, and diagrams.
    """

    @classmethod
    def clean_and_brand_pdf(
        cls,
        pdf_input: Union[bytes, str, Path],
        output_path: Optional[Union[str, Path]] = None,
        apply_cleanup: bool = True,
        apply_branding: bool = True
    ) -> bytes:
        if isinstance(pdf_input, (str, Path)):
            doc = pymupdf.open(str(pdf_input))
        else:
            doc = pymupdf.open(stream=pdf_input, filetype="pdf")

        for page in doc:
            rect = page.rect
            width = rect.width
            height = rect.height

            if apply_cleanup:
                cls._clean_page_noise(page, width, height)

            if apply_branding:
                cls._add_portal_branding(page, width, height)

        if output_path:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(out_file), garbage=3, deflate=True)
            doc.close()
            return out_file.read_bytes()

        output_bytes = doc.tobytes(garbage=3, deflate=True)
        doc.close()
        return output_bytes

    @classmethod
    def _clean_page_noise(cls, page: pymupdf.Page, width: float, height: float) -> None:
        has_redactions = False

        for annot in list(page.annots()):
            try:
                info = annot.info
                if info and info.get("subject", "").lower() == "watermark":
                    page.delete_annot(annot)
            except Exception:
                pass

        blocks = page.get_text("blocks")
        for b in blocks:
            b_x0, b_y0, b_x1, b_y1, b_text, *_ = b
            b_rect = pymupdf.Rect(b_x0, b_y0, b_x1, b_y1)

            for pattern in DE_WATERMARK_PATTERNS:
                if pattern.search(b_text):
                    page.add_redact_annot(b_rect, fill=(1, 1, 1))
                    has_redactions = True
                    break

        if has_redactions:
            try:
                page.apply_redactions()
            except Exception as e:
                logger.debug("Failed applying redactions on page %s: %s", page.number, e)

    @classmethod
    def _add_portal_branding(cls, page: pymupdf.Page, width: float, height: float) -> None:
        cx = width / 2.0
        cy = height / 2.0
        host = _portal_host()
        watermark_text = f"{host} - {BRAND_NAME}"
        footer_text = f"🌐 {BRAND_NAME} | {host}"

        fontsize = 32.0
        text_len = pymupdf.get_text_length(watermark_text, fontsize=fontsize)
        start_point = pymupdf.Point(cx - text_len / 2.0, cy)

        morph_center = pymupdf.Point(cx, cy)
        rot_matrix = pymupdf.Matrix(-35)

        try:
            page.insert_text(
                start_point,
                watermark_text,
                fontsize=fontsize,
                color=WATERMARK_COLOR,
                morph=(morph_center, rot_matrix),
                overlay=False,
                fill_opacity=0.07
            )
        except Exception as e:
            logger.debug("Failed to insert center watermark on page %s: %s", page.number, e)

        footer_point = pymupdf.Point(36, height - 12)
        try:
            page.insert_text(
                footer_point,
                footer_text,
                fontsize=7.5,
                color=FOOTER_COLOR,
                overlay=True
            )
        except Exception as e:
            logger.debug("Failed to insert footer bar on page %s: %s", page.number, e)
