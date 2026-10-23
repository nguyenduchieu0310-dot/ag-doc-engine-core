"""
Indexer Sentinel Connector (AG DocEngine Core v3.0).
Notifies IndexNow (Bing, Yandex, Seznam) and Search Engines immediately upon publication.
Generates Google News Sitemap XML structures dynamically from `configs/domain.config.json`.
"""

import json
import logging
import os
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import requests

from core.config import BRAND_NAME, PUBLIC_BASE_URL
from core.domain_config import get_brand_config

logger = logging.getLogger("ag.indexer_sentinel")

_brand = get_brand_config()
INDEXNOW_API_ENDPOINT = "https://api.indexnow.org/indexnow"
DEFAULT_HOST = urllib.parse.urlsplit(PUBLIC_BASE_URL).hostname or _brand.get("domain", "docs.example.com")
DEFAULT_INDEXNOW_KEY = os.getenv("INDEXNOW_KEY", "ag-doc-engine-indexnow-key-2026")


class IndexerSentinel:
    """Instant Search Engine Notification & Indexing Dispatcher."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        indexnow_key: str = DEFAULT_INDEXNOW_KEY,
        timeout: int = 15,
    ):
        self.host = host
        self.key = indexnow_key
        self.key_location = f"https://{self.host}/{self.key}.txt"
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"AG-IndexerSentinel/3.0 (+{PUBLIC_BASE_URL})",
            "Content-Type": "application/json; charset=utf-8",
        })

    def notify_indexnow(self, urls: List[str]) -> Dict[str, Any]:
        if not urls:
            return {"success": True, "count": 0, "message": "No URLs provided"}

        normalized_urls = []
        for u in urls:
            if u.startswith("/"):
                normalized_urls.append(f"https://{self.host}{u}")
            elif not u.startswith("http"):
                normalized_urls.append(f"https://{self.host}/{u.lstrip('/')}")
            else:
                normalized_urls.append(u)

        payload = {
            "host": self.host,
            "key": self.key,
            "keyLocation": self.key_location,
            "urlList": normalized_urls[:1000],
        }

        try:
            resp = self.session.post(
                INDEXNOW_API_ENDPOINT,
                data=json.dumps(payload),
                timeout=self.timeout,
            )
            success = resp.status_code in (200, 202)
            if success:
                logger.info(
                    "IndexNow ping successful for %d URLs (Status %d)",
                    len(normalized_urls),
                    resp.status_code,
                )
            else:
                logger.warning(
                    "IndexNow ping returned status %d: %s",
                    resp.status_code,
                    resp.text[:200],
                )

            return {
                "success": success,
                "status_code": resp.status_code,
                "count": len(normalized_urls),
                "response": resp.text[:200] if not success else "OK",
            }
        except Exception as e:
            logger.error("Failed to notify IndexNow: %s", e)
            return {"success": False, "error": str(e), "count": len(normalized_urls)}

    def ping_sitemaps(self, sitemap_url: Optional[str] = None) -> Dict[str, Any]:
        target_sitemap = sitemap_url or f"https://{self.host}/sitemap.xml"
        encoded = urllib.parse.quote(target_sitemap, safe="")
        ping_endpoints = {
            "google": f"https://www.google.com/ping?sitemap={encoded}",
            "bing": f"https://www.bing.com/ping?sitemap={encoded}",
        }

        results = {}
        for engine, ping_url in ping_endpoints.items():
            try:
                resp = requests.get(ping_url, timeout=10)
                results[engine] = {
                    "status_code": resp.status_code,
                    "success": resp.status_code in (200, 204),
                }
                logger.info("Pinged %s sitemap: HTTP %d", engine, resp.status_code)
            except Exception as e:
                results[engine] = {"success": False, "error": str(e)}
                logger.warning("Ping to %s sitemap failed: %s", engine, e)

        return results

    @staticmethod
    def build_google_news_xml_entry(
        canonical_url: str,
        title: str,
        publication_date_iso: str,
        publication_name: str = BRAND_NAME,
        language: str = "vi",
    ) -> str:
        from xml.sax.saxutils import escape
        safe_url = escape(canonical_url)
        safe_title = escape(title)
        safe_pub = escape(publication_name)
        return (
            f"  <url>\n"
            f"    <loc>{safe_url}</loc>\n"
            f"    <news:news>\n"
            f"      <news:publication>\n"
            f"        <news:name>{safe_pub}</news:name>\n"
            f"        <news:language>{language}</news:language>\n"
            f"      </news:publication>\n"
            f"      <news:publication_date>{publication_date_iso}</news:publication_date>\n"
            f"      <news:title>{safe_title}</news:title>\n"
            f"    </news:news>\n"
            f"  </url>"
        )
