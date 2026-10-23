import os
import tempfile
import unittest
from pathlib import Path

import pymupdf

from core.domain_config import (
    DOMAIN_CONFIG,
    get_brand_config,
    get_taxonomy_config,
     get_temporal_policy,
    reload_domain_config,
)
from processing.seo_geo_enricher import SEOGEOEnricher
from processing.temporal_guard import TemporalYearGuard
from services.agent_content_processor import ContentProcessorAgent
from services.agent_qa_sentinel import QASentinelAgent
from cloudflare.d1_deployer import CloudflareD1Deployer


def _make_sample_pdf(path: Path, text: str = "Tai lieu chuyen sau nam 2026\nPhan I: Tong quan\nCau 1: Noi dung phan tich chi tiet he thong.") -> Path:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), text, fontsize=14)
    doc.save(str(path))
    doc.close()
    return path


class TestAGDocEngineCore(unittest.TestCase):
    def setUp(self):
        os.environ.pop("AG_DOMAIN_CONFIG", None)
        reload_domain_config()

    def tearDown(self):
        os.environ.pop("AG_DOMAIN_CONFIG", None)
        reload_domain_config()

    def test_default_domain_config_is_domain_agnostic(self):
        brand = get_brand_config()
        tax = get_taxonomy_config()
        policy = get_temporal_policy()
        self.assertEqual(brand.get("name"), "AG DocPortal")
        self.assertEqual(tax.get("require_formulas_for_categories"), [])
        self.assertGreaterEqual(policy.get("min_eligible_year", 0), 2023)

    def test_preset_switching_general_legal_and_stem(self):
        base_dir = Path(__file__).resolve().parent.parent

        # 1. Legal Preset
        reload_domain_config(base_dir / "presets" / "legal-business.json")
        self.assertEqual(get_taxonomy_config()["default_category"], "Pháp chế Doanh nghiệp")
        meta_legal = SEOGEOEnricher.enrich(
            "Mẫu Hợp đồng Thương mại và Quản trị Doanh nghiệp năm 2026 - Sở Kế hoạch và Đầu tư Hà Nội"
        )
        self.assertEqual(meta_legal.subject, "Hợp đồng Thương mại")
        self.assertEqual(meta_legal.document_type, "Mẫu Hợp đồng")
        self.assertEqual(meta_legal.academic_year, "2026")

        # 2. Education STEM Preset
        reload_domain_config(base_dir / "presets" / "education-stem.json")
        self.assertIn("Toán", get_taxonomy_config()["require_formulas_for_categories"])
        meta_stem = SEOGEOEnricher.enrich(
            "Đề thi thử Tốt nghiệp THPT năm 2026 môn Toán lớp 12 trường THPT Chuyên Hà Nội"
        )
        self.assertEqual(meta_stem.subject, "Toán")
        self.assertEqual(meta_stem.grade, "Cấp 3 (THPT)")
        self.assertEqual(meta_stem.document_type, "Đề thi & Kiểm tra")

        # 3. General Docs Preset
        reload_domain_config(base_dir / "presets" / "general-docs.json")
        meta_gen = SEOGEOEnricher.enrich(
            "Báo cáo Phân tích Trí tuệ Nhân tạo AI và Dữ liệu năm 2026 cấp Chuyên sâu"
        )
        self.assertEqual(meta_gen.subject, "Công nghệ & Kỹ thuật")
        self.assertEqual(meta_gen.grade, "Chuyên sâu")
        self.assertEqual(meta_gen.document_type, "Báo cáo phân tích")

    def test_temporal_year_guard_filters_old_documents(self):
        res_new = TemporalYearGuard.evaluate(
            title="Cẩm nang Chuyển đổi số Doanh nghiệp 2026",
            url="https://docs.example.com/2026/05/cam-nang.pdf"
        )
        self.assertTrue(res_new.is_eligible)
        self.assertEqual(res_new.detected_year, 2026)

        res_old = TemporalYearGuard.evaluate(
            title="Tài liệu lưu trữ năm 2019",
            url="https://docs.example.com/2019/05/tai-lieu.pdf"
        )
        self.assertFalse(res_old.is_eligible)

    def test_content_processor_and_qa_sentinel_100_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw_pdf = _make_sample_pdf(
                tmp_path / "raw.pdf",
                "Bao cao Cong nghe AI 2026\nLien he Zalo: 0912345678\nPhan I: Kien truc he thong\nCau 1: Phân tích hệ thống dữ liệu lớn và trí tuệ nhân tạo trong doanh nghiệp."
            )
            processor = ContentProcessorAgent()
            draft = processor.process_raw_document(
                raw_pdf_path=raw_pdf,
                item_meta={
                    "title": "Báo cáo Phân tích Công nghệ AI và Hệ thống Dữ liệu năm 2026 bản chuẩn",
                    "url": "https://docs.example.com/2026/bao-cao-ai-cloud-2026",
                    "published_year": 2026,
                },
                source={"primary_category": "Công nghệ & Kỹ thuật"},
                output_dir=tmp_path / "work",
            )
            sentinel = QASentinelAgent()
            report = sentinel.audit_draft_package(draft)
            self.assertTrue(report.is_approved, f"Expected 100% pass, defects: {report.defects}")
            self.assertEqual(report.overall_score, 100.0)

    def test_qa_sentinel_self_healing_when_latex_required(self):
        base_dir = Path(__file__).resolve().parent.parent
        reload_domain_config(base_dir / "presets" / "education-stem.json")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw_pdf = _make_sample_pdf(
                tmp_path / "stem.pdf",
                "De thi Toan lop 12 nam 2026\nPhan I: Trac nghiem\nCau 1: Cho ham so bac ba tren tap so thuc."
            )
            processor = ContentProcessorAgent()
            draft = processor.process_raw_document(
                raw_pdf_path=raw_pdf,
                item_meta={
                    "title": "Đề thi thử môn Toán lớp 12 năm 2026 trường THPT Chuyên Hà Nội",
                    "url": "https://edu.example.com/2026/de-thi-toan-12-2026",
                    "published_year": 2026,
                },
                source={"primary_category": "Toán"},
                output_dir=tmp_path / "work",
            )
            # Deliberately strip '$' to test self-healing loop between Agent 2 and Agent 1
            draft["description"] = draft["description"].replace("$", "")
            sentinel = QASentinelAgent()
            report_before = sentinel.audit_draft_package(draft)
            self.assertFalse(report_before.is_approved)
            self.assertTrue(any("KaTeX" in d for d in report_before.defects))

            healed = processor.refine_draft_package(draft, report_before.defects)
            report_after = sentinel.audit_draft_package(healed)
            self.assertTrue(report_after.is_approved, f"Self-healed draft should pass 100%: {report_after.defects}")

    def test_d1_deployer_uses_substr_instead_of_long_like_pattern(self):
        deployer = CloudflareD1Deployer(
            account_id="acc-123",
            database_id="db-123",
            api_token="token-123"
        )
        captured_sql = []
        def fake_exec(sql, params=None):
            captured_sql.append((sql, params))
            return {"success": True, "result": [{"success": True, "results": []}]}
        deployer.execute_raw_sql = fake_exec

        found = deployer.find_existing_document("https://docs.example.com/2026/doc-1", "doc-1-slug")
        self.assertIsNone(found)
        self.assertEqual(len(captured_sql), 1)
        sql, params = captured_sql[0]
        self.assertIn("substr(source_object_key,1,50)=?", sql)
        self.assertNotIn("LIKE", sql)
        self.assertEqual(len(params[1]), 50)


if __name__ == "__main__":
    unittest.main()
