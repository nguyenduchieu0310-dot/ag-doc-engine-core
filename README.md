# 🚀 AG DocEngine Core v3.0 — Autonomous Document Ingestion, Sanitization, QA & Publishing Engine

**AG DocEngine Core v3.0** là công nghệ lõi tự hành 24/7/365 (**100% Domain-Agnostic** — độc lập chủ đề và thương hiệu) chuyên thực hiện chu trình khép kín:
> **Quét nguồn tự động (Crawl) $\rightarrow$ Khử trùng dữ liệu nhạy cảm (Deep Sanitizer) $\rightarrow$ Kết xuất bìa HD $\ge 1200\text{px}$ $\rightarrow$ Biên tập SEO/GEO 4 Phần $\rightarrow$ Kiểm định độc lập 10 Cổng QA (Self-Healing) $\rightarrow$ Xuất bản lên Cloudflare D1 + R2 & Edge Dashboard.**

---

## ✨ Điểm mạnh Cốt lõi

1. **100% Độc lập Chủ đề (Zero Domain Hardcoding)**:
   - Chuyển đổi sang bất kỳ ngành nghề hoặc website nào (Pháp luật, Biểu mẫu Doanh nghiệp, Y tế, Bất động sản, Công nghệ/AI, Giáo dục STEM...) chỉ bằng cách chỉnh sửa duy nhất tệp [`configs/domain.config.json`](configs/domain.config.json) hoặc chọn từ [`presets/`](presets/).
2. **Kiến trúc 3-Agent Tự chữa lành (Self-Healing Multi-Agent Pipeline)**:
   - **Agent 1 (`ContentProcessorAgent`)**: Tải tệp gốc (chỉ nhận PDF/Word/PowerPoint, chặn 100% file ảnh rác), chuyển đổi LibreOffice sang PDF, xóa sạch 100% SĐT/Zalo/link quảng cáo/watermark bên thứ ba, tạo ảnh bìa chuẩn Google Discover ($\ge 1200\text{px}$, $\le 250\text{KiB}$), trích xuất văn bản thật từng trang để viết bài phân tích 4 phần kèm Dual Schema JSON-LD.
   - **Agent 2 (`QASentinelAgent`)**: Giám khảo độc lập chấm điểm 10 cổng QA trên 4 trụ cột (SEO, GEO/E-E-A-T, Google Discover, Safety). Nếu điểm $< 100/100$, tự động trả phiếu lỗi (`defects`) để Agent 1 tự sửa chữa.
   - **Agent 3 (`AutoPublisherAgent`)**: Chỉ xuất bản tài liệu đạt tuyệt đối `100/100` lên Cloudflare R2 + D1 và ping lập chỉ mục tự động (Google Indexing & IndexNow).
3. **Chi phí Biến phí $0 (Zero Variable Cost Architecture)**:
   - Toàn bộ quá trình trích xuất văn bản, khử trùng PII, đóng dấu thương hiệu ngầm và kiểm định 10 cổng được xử lý bằng thuật toán Deterministic trên PyMuPDF + Pillow (không tốn phí token LLM cho từng tài liệu), kết hợp gói cố định của Cloudflare Workers/D1/R2 và GitHub Actions.

---

## 📂 Cấu trúc Dự án

```text
AG-DocEngine-Core/
├── configs/
│   ├── domain.config.json          # Cấu hình Thương hiệu, Taxonomy & Bố cục bài viết (Active)
│   └── sources_registry.json       # Danh sách nguồn cào (Sitemap, RSS, Blogger, HTML)
├── presets/                        # Các mẫu cấu hình dựng sẵn theo ngành nghề
│   ├── general-docs.json           # Đa ngành: Kinh doanh, Công nghệ, Tài chính, Nghiên cứu
│   ├── legal-business.json         # Pháp lý: Văn bản luật, Hợp đồng, Biểu mẫu doanh nghiệp
│   └── education-stem.json         # Giáo dục & STEM (Bật kiểm định công thức KaTeX)
├── core/                           # Bộ nạp cấu hình động, Rate Limiter, Worker Pool
├── adapters/                       # Các Adapter cào dữ liệu (Sitemap, RSS, Blogger, HTML)
├── processing/                     # Downloader, PDF Converter, Smart Watermark, SEO/GEO Enricher
├── services/                       # Bộ 3 Agent (Processor, QA Sentinel, Auto Publisher)
├── cloudflare/                     # Tích hợp Cloudflare D1, R2, Cloud Ledger & Ingest API
├── cloudflare-edge-dashboard/      # Giao diện Dashboard quản trị 24/7 trên Cloudflare Workers
├── .agents/skills/ag-doc-engine-core/ # Kỹ năng tự động hóa sẵn sàng cho Antigravity (AGY)
└── tests/                          # Bộ kiểm thử tự động (Unit Tests)
```

---

## ⚡ Hướng dẫn Bắt đầu Nhanh (Quick Start)

### 1. Chuyển đổi sang Ngành nghề / Website mới
Sao chép một preset từ `presets/` vào `configs/domain.config.json`:
```powershell
Copy-Item presets/legal-business.json configs/domain.config.json -Force
```
Sau đó mở `configs/domain.config.json` để điền tên thương hiệu (`brand.name`), tên miền (`brand.public_base_url`) và danh mục chuyên ngành (`taxonomy`).

### 2. Chạy Kiểm thử Tự động (Unit Tests)
```powershell
uv run --with pymupdf --with pillow --with pypdf --with requests --with beautifulsoup4 python -m unittest discover -s tests -p "test_*.py" -v
```

### 3. Triển khai lên Cloudflare & GitHub Actions
- Khai báo các Secrets trong GitHub Repository:
  - `CLOUDFLARE_ACCOUNT_ID`
  - `CLOUDFLARE_D1_DATABASE_ID`
  - `CLOUDFLARE_R2_BUCKET`
  - `CLOUDFLARE_API_TOKEN`
  - `DOCUMENT_INGEST_TOKEN`
- Đặt biến Repository Variable `AG_CLOUD_ENABLED=true` khi sẵn sàng chạy tự động 4 tiếng/lần.
