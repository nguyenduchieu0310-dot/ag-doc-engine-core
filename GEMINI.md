# QUY TẮC DỰ ÁN: AG DOC-ENGINE CORE v3.0 (DOMAIN-AGNOSTIC ENGINE)

## 1. NGUYÊN TẮC CỐT LÕI: TỰ ĐỘNG QUYẾT ĐỊNH PHƯƠNG ÁN TỐI ƯU
- **Ủy quyền toàn diện**: Người dùng đã thiết lập nguyên tắc: **"Cho Gemini tự chọn phương án mà Gemini cho là tối ưu nhất"**.
- **Không hỏi lại các quyết định kỹ thuật**: Tự động đánh giá ưu/nhược điểm theo tiêu chuẩn kỹ thuật cao nhất và chọn ngay phương án tối ưu nhất để thực thi liên tục cho đến khi hoàn thành mục tiêu.

## 2. CẤU TRÚC THƯ MỤC CHUẨN (`AG-DocEngine-Core`)
- `configs/domain.config.json`: Cấu hình trung tâm (Thương hiệu, Tên miền, Phân loại Taxonomy, Template bài viết 4 phần, Chính sách năm phát hành).
- `configs/sources_registry.json`: Danh sách các nguồn cào (RSS, Sitemap, Blogger API, HTML Spider).
- `presets/`: Các bộ cấu hình mẫu dựng sẵn cho nhiều ngành nghề:
  - `presets/general-docs.json`: Cổng tài liệu Đa ngành (Kinh doanh, Công nghệ & AI, Tài chính, Nghiên cứu).
  - `presets/legal-business.json`: Cổng Văn bản Pháp luật, Hợp đồng & Biểu mẫu Doanh nghiệp.
  - `presets/education-stem.json`: Cổng Học liệu Giáo dục & STEM (bật kiểm tra công thức KaTeX `$...$`).
- `core/`: Bộ nạp cấu hình động (`domain_config.py`, `config.py`), SQLite queue cục bộ, Rate Limiter, Worker Pool.
- `adapters/`: Các bộ thu thập dữ liệu đa giao thức (Sitemap, RSS, Blogger JSON, HTML Spider).
- `processing/`: Bộ tải tệp chống lỗi (`file_downloader.py`), chuyển đổi Office sang PDF (`pdf_converter.py`), đóng dấu thương hiệu ngầm (`smart_watermark_engine.py`), làm giàu SEO/GEO (`seo_geo_enricher.py`), lọc năm phát hành (`temporal_guard.py`).
- `services/`:
  - `agent_content_processor.py` (Agent 1: Làm sạch + Render bìa HD + Viết bài 4 phần + Schema.org).
  - `agent_qa_sentinel.py` (Agent 2: Kiểm định độc lập 10 cổng QA & Tự chữa lành).
  - `agent_auto_publisher.py` (Agent 3: Xuất bản tự động lên D1 + R2 & Ping IndexNow).
  - `multi_agent_orchestrator.py`: Nhạc trưởng điều phối vòng lặp `Agent 1 <-> Agent 2 -> Agent 3`.
- `cloudflare/`: Tích hợp Cloudflare D1 (`d1_deployer.py`, `cloud_ledger.py`), Cloudflare R2 (`r2_uploader.py`), Ingest API (`document_ingest.py`).
- `cloudflare-edge-dashboard/`: Giao diện Dashboard quản trị & theo dõi thời gian thực trên Cloudflare Workers (`AG DOC-ENGINE CORE v3.0`).
