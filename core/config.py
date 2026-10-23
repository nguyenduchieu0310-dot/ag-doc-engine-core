import os
import sys
from pathlib import Path
from typing import Optional

from core.domain_config import get_brand_config, get_temporal_policy

# Ensure UTF-8 console output on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_brand = get_brand_config()
_temporal = get_temporal_policy()

# Base project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("AG_DATA_DIR", os.getenv("BEEKIP_DATA_DIR", str(BASE_DIR / "data"))))
LOGS_DIR = DATA_DIR / "logs"
DOWNLOADS_DIR = DATA_DIR / "downloads"
DOWNLOADS_PDF_DIR = DOWNLOADS_DIR / "pdf"
DOWNLOADS_WORD_DIR = DOWNLOADS_DIR / "word"
DOWNLOADS_PPT_DIR = DOWNLOADS_DIR / "powerpoint"
PROCESSED_DIR = DATA_DIR / "processed"
EXPORTS_DIR = DATA_DIR / "exports"

# Allowed canonical document formats: Strictly PDF, Word, PowerPoint (Reject all standalone images)
ALLOWED_DOC_EXTENSIONS = {".pdf", ".docx", ".doc", ".pptx", ".ppt"}
DISALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico", ".tiff", ".avif"}

DB_PATH = DATA_DIR / "crawler_state.db"
SOURCES_REGISTRY_PATH = Path(
    os.getenv("AG_SOURCES_REGISTRY", str(BASE_DIR / "configs" / "sources_registry.json"))
)
SITEMAP_PATH = DATA_DIR / "sitemap.xml"

# Ensure runtime directories exist
for path in [DATA_DIR, LOGS_DIR, DOWNLOADS_DIR, DOWNLOADS_PDF_DIR, DOWNLOADS_WORD_DIR, DOWNLOADS_PPT_DIR, PROCESSED_DIR, EXPORTS_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# User-Agent simulation
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# Minimum eligible publication year (configurable via domain.config.json)
MIN_ELIGIBLE_YEAR = int(os.getenv("MIN_ELIGIBLE_YEAR", str(_temporal.get("min_eligible_year", 2023))))

# Sources restricted to delta monitoring only
MONITOR_ONLY_SOURCE_IDS = set(
    s.strip() for s in os.getenv("MONITOR_ONLY_SOURCE_IDS", "").split(",") if s.strip()
)

# Concurrency & Rate Limiting SLAs
MAX_WORKER_THREADS = int(os.getenv("MAX_WORKER_THREADS", "20"))
FAST_DOWNLOAD_WORKERS = int(os.getenv("FAST_DOWNLOAD_WORKERS", "20"))
MAX_DOMAIN_CONCURRENCY = int(os.getenv("MAX_DOMAIN_CONCURRENCY", "4"))
MIN_DOMAIN_DELAY_SECONDS = float(os.getenv("MIN_DOMAIN_DELAY_SECONDS", "0.4"))
MAX_DOMAIN_DELAY_SECONDS = float(os.getenv("MAX_DOMAIN_DELAY_SECONDS", "1.0"))
RATE_LIMIT_BACKOFF_SECONDS = float(os.getenv("RATE_LIMIT_BACKOFF_SECONDS", "30.0"))

# Scheduler Config
MONITOR_INTERVAL_HOURS = 4
SCHEDULED_RUN_HOURS = [0, 4, 8, 12, 16, 20]  # UTC+7 Operating schedule

# Cloudflare & Brand Portal Configuration (Overridable via Environment Variables or domain.config.json)
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CLOUDFLARE_D1_DATABASE_ID = os.getenv("CLOUDFLARE_D1_DATABASE_ID", "")
CLOUDFLARE_R2_BUCKET = os.getenv("CLOUDFLARE_R2_BUCKET", "")
R2_PUBLIC_BASE_URL = os.getenv(
    "R2_PUBLIC_BASE_URL",
    _brand.get("files_base_url", "https://files.example.com"),
)
PUBLIC_BASE_URL = os.getenv(
    "PUBLIC_BASE_URL",
    os.getenv("BEEKIP_BASE_URL", _brand.get("public_base_url", "https://docs.example.com")),
)
# Alias for backwards compatibility with modules importing BEEKIP_BASE_URL
BEEKIP_BASE_URL = PUBLIC_BASE_URL
DOCUMENT_ROUTE_PREFIX = os.getenv(
    "DOCUMENT_ROUTE_PREFIX",
    _brand.get("document_route_prefix", "/tai-lieu"),
)
BRAND_NAME = os.getenv("BRAND_NAME", _brand.get("name", "AG DocPortal"))
BRAND_FULL_NAME = os.getenv("BRAND_FULL_NAME", _brand.get("full_name", "AG Autonomous Document Portal"))
DEFAULT_AUTHOR_NAME = os.getenv(
    "DEFAULT_AUTHOR_NAME",
    _brand.get("default_author", "Ban Biên Tập & Số Hóa Tài Liệu"),
)


def get_cloudflare_token() -> Optional[str]:
    """
    Resolve Cloudflare API token dynamically:
    1. CLOUDFLARE_API_TOKEN environment variable.
    2. Local or user wrangler configuration file (default.toml).
    """
    env_token = os.getenv("CLOUDFLARE_API_TOKEN")
    if env_token:
        return env_token.strip()

    candidate_toml_paths = [
        Path(os.environ.get("APPDATA", "")) / "Roaming" / "xdg.config" / ".wrangler" / "config" / "default.toml",
        Path(os.environ.get("USERPROFILE", "")) / "AppData" / "Roaming" / "xdg.config" / ".wrangler" / "config" / "default.toml",
        Path.home() / ".wrangler" / "config" / "default.toml",
        BASE_DIR / ".wrangler" / "config" / "default.toml",
    ]

    for p in candidate_toml_paths:
        try:
            if p.is_file():
                for line in p.read_text(encoding="utf-8").splitlines():
                    clean_line = line.strip()
                    if clean_line.startswith("oauth_token"):
                        token = clean_line.split("=", 1)[1].strip().strip('"').strip("'")
                        if token:
                            return token
        except Exception:
            continue

    return None
