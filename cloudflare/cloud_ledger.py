"""Small durable D1 ledger, independent of runner disk and Actions caches.
Table names default to `ag_crawler_queue`, `ag_crawler_sources`, `ag_crawler_blobs`
(configurable in `configs/domain.config.json`).
"""
import json
import re
from pathlib import Path
from core.config import SOURCES_REGISTRY_PATH
from core.domain_config import get_storage_config


def _safe_identifier(name: str, default: str) -> str:
    return name if re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", str(name or "")) else default


class CloudLedger:
    def __init__(self, client):
        self.client = client
        self.sources = []
        storage = get_storage_config()
        self.queue_table = _safe_identifier(storage.get("queue_table", ""), "ag_crawler_queue")
        self.sources_table = _safe_identifier(storage.get("sources_table", ""), "ag_crawler_sources")
        self.blobs_table = _safe_identifier(storage.get("blobs_table", ""), "ag_crawler_blobs")

    def query(self, sql, params=None):
        return self.client.execute_raw_sql(sql, params)["result"][0].get("results", [])

    def initialize(self):
        for sql in (
            f"CREATE TABLE IF NOT EXISTS {self.queue_table} (url TEXT PRIMARY KEY, source_id TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING', retry_count INTEGER NOT NULL DEFAULT 0, error_message TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)",
            f"CREATE INDEX IF NOT EXISTS {self.queue_table}_status ON {self.queue_table}(status,retry_count,created_at)",
            f"CREATE TABLE IF NOT EXISTS {self.sources_table} (source_id TEXT PRIMARY KEY,last_etag TEXT,last_modified_header TEXT,last_checked_at TEXT)",
            f"CREATE TABLE IF NOT EXISTS {self.blobs_table} (sha256_hash TEXT PRIMARY KEY,file_size_bytes INTEGER NOT NULL,r2_storage_key TEXT NOT NULL,public_file_url TEXT NOT NULL,first_seen_url TEXT)",
        ):
            self.query(sql)
        self.query(f"UPDATE {self.queue_table} SET status='PENDING' WHERE status='PROCESSING'")

    def sync_sources_from_json(self, registry_file=SOURCES_REGISTRY_PATH):
        self.sources = json.loads(Path(registry_file).read_text(encoding="utf-8"))
        return len(self.sources)

    def get_active_sources(self):
        state = {r["source_id"]: r for r in self.query(f"SELECT * FROM {self.sources_table}")}
        active = [
            dict(src, **{k: v for k, v in state.get(src["source_id"], {}).items() if k != "source_id"})
            for src in self.sources
            if src.get("status") == "ACTIVE"
        ]
        return sorted(active, key=lambda s: (s.get("last_checked_at") or "", s["source_id"]))

    def update_source_sync_meta(self, source_id, etag=None, last_modified=None, **kwargs):
        self.query(
            f"INSERT INTO {self.sources_table} VALUES (?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(source_id) DO UPDATE SET last_etag=COALESCE(excluded.last_etag,last_etag),last_modified_header=COALESCE(excluded.last_modified_header,last_modified_header),last_checked_at=excluded.last_checked_at",
            [source_id, etag, last_modified],
        )

    def enqueue_inbound_items(self, items):
        for item in items:
            self.query(
                f"INSERT INTO {self.queue_table} (url,source_id,payload,status) VALUES (?,?,?,?) ON CONFLICT(url) DO NOTHING",
                [item["url"], item["source_id"], json.dumps(item, ensure_ascii=False), item.get("status", "PENDING")],
            )
        return len(items)

    def get_pending_inbound_items(self, limit=3, **kwargs):
        rows = self.query(
            f"SELECT payload FROM {self.queue_table} WHERE status IN ('PENDING','FAILED') AND retry_count<3 ORDER BY created_at,url LIMIT ?",
            [limit],
        )
        return [json.loads(row["payload"]) for row in rows]

    def update_inbound_status(self, url, status, error_message=None, increment_retry=False):
        self.query(
            f"UPDATE {self.queue_table} SET status=?,error_message=?,retry_count=retry_count+? WHERE url=?",
            [status, error_message, int(increment_retry), url],
        )

    def get_blob_by_hash(self, sha256):
        rows = self.query(f"SELECT * FROM {self.blobs_table} WHERE sha256_hash=?", [sha256])
        return rows[0] if rows else None

    def record_file_blob(self, sha256_hash, file_size_bytes, r2_storage_key, public_file_url, first_seen_url=None):
        self.query(
            f"INSERT INTO {self.blobs_table} VALUES (?,?,?,?,?) ON CONFLICT(sha256_hash) DO NOTHING",
            [sha256_hash, file_size_bytes, r2_storage_key, public_file_url, first_seen_url],
        )

    def stored_bytes(self):
        return self.query(f"SELECT COALESCE(SUM(file_size_bytes),0) AS total FROM {self.blobs_table}")[0]["total"]

    def create_monitoring_cycle(self, cycle_id):
        pass

    def complete_monitoring_cycle(self, **kwargs):
        pass
