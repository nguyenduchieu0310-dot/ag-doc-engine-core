"""
Domain-Agnostic Configuration Loader for AG DocEngine Core v3.0.
Loads `configs/domain.config.json` (or the path specified via `AG_DOMAIN_CONFIG`)
so the entire 3-Agent pipeline can be applied to ANY website or industry vertical
without modifying Core Engine source code.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DOMAIN_CONFIG_PATH = BASE_DIR / "configs" / "domain.config.json"


def load_domain_config(config_path: str | Path | None = None) -> Dict[str, Any]:
    resolved = Path(
        config_path
        or os.getenv("AG_DOMAIN_CONFIG", "")
        or DEFAULT_DOMAIN_CONFIG_PATH
    )
    if resolved.is_file():
        return json.loads(resolved.read_text(encoding="utf-8"))
    return {
        "schema_version": "3.0.0",
        "preset_id": "general-docs",
        "brand": {
            "name": "AG DocPortal",
            "full_name": "AG Autonomous Document Portal",
            "domain": "docs.example.com",
            "public_base_url": "https://docs.example.com",
            "files_base_url": "https://files.example.com",
            "document_route_prefix": "/tai-lieu",
            "dashboard_title": "AG DOC-ENGINE CORE v3.0",
            "dashboard_subtitle": "Autonomous Crawl • Deep Sanitizer • HD Cover • QA Sentinel 100/100",
            "default_author": "Ban Biên Tập & Số Hóa Tài Liệu",
        },
        "temporal_policy": {
            "min_eligible_year": 2023,
            "always_accept_keywords": ["mới nhất", "cập nhật"],
        },
        "taxonomy": {
            "category_label": "Chuyên mục",
            "level_label": "Phân nhóm / Cấp độ",
            "organization_label": "Đơn vị phát hành",
            "default_category": "Tài liệu chuyên ngành",
            "default_level": "Tiêu chuẩn",
            "default_document_type": "Tài liệu hướng dẫn",
            "default_framework": "Chuẩn Quốc gia & Quốc tế",
            "require_formulas_for_categories": [],
            "categories": [],
            "document_types": [],
            "levels": [],
            "frameworks": [],
        },
        "article_template": {
            "section_1_title": "1. Tổng quan & Hồ sơ xác thực tài liệu",
            "section_2_title": "2. Phân tích cấu trúc & Nội dung trọng tâm",
            "section_3_title": "3. Phụ lục, Biểu mẫu & Dữ liệu đối chiếu",
            "section_4_title": "4. Giá trị ứng dụng & Hướng dẫn khai thác",
            "appendix_present_label": "Có kèm phụ lục / hướng dẫn chi tiết trong tệp",
            "appendix_absent_label": "Tài liệu nguyên bản (chưa kèm phụ lục giải thích riêng)",
        },
        "storage": {
            "queue_table": "ag_crawler_queue",
            "sources_table": "ag_crawler_sources",
            "blobs_table": "ag_crawler_blobs",
        },
    }


DOMAIN_CONFIG: Dict[str, Any] = load_domain_config()


def reload_domain_config(config_path: str | Path | None = None) -> Dict[str, Any]:
    """Reloads DOMAIN_CONFIG in-place so all modules immediately see the active preset."""
    loaded = load_domain_config(config_path)
    DOMAIN_CONFIG.clear()
    DOMAIN_CONFIG.update(loaded)
    return DOMAIN_CONFIG


def get_brand_config() -> Dict[str, Any]:
    return DOMAIN_CONFIG.get("brand", {})


def get_taxonomy_config() -> Dict[str, Any]:
    return DOMAIN_CONFIG.get("taxonomy", {})


def get_article_template_config() -> Dict[str, Any]:
    return DOMAIN_CONFIG.get("article_template", {})


def get_temporal_policy() -> Dict[str, Any]:
    return DOMAIN_CONFIG.get("temporal_policy", {})


def get_storage_config() -> Dict[str, Any]:
    return DOMAIN_CONFIG.get("storage", {})
