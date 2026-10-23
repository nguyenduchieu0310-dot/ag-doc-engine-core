---
name: ag-doc-engine-core
description: Khởi tạo, cấu hình chủ đề/ngành nghề mới, vận hành và kiểm định hệ thống AG DocEngine Core v3.0 (Cào bài viết -> Làm sạch Deep Sanitizer -> Kiểm định QA 10/10 -> Xuất bản tự động Cloudflare D1 + R2 & Edge Dashboard).
---

# Kỹ năng: AG DocEngine Core v3.0 (`ag-doc-engine-core`)

Sử dụng kỹ năng này bất cứ khi nào người dùng yêu cầu:
1. Áp dụng công nghệ **AG DocEngine Core v3.0** cho một website mới hoặc một lĩnh vực/chủ đề mới (Pháp lý, Y tế, Bất động sản, Công nghệ, Kinh doanh, Giáo dục...).
2. Thêm nguồn cào mới (Sitemap, RSS, HTML, Blogger API) vào hệ thống.
3. Chạy kiểm định chất lượng 10 cổng QA Gate, tùy chỉnh quy tắc làm sạch PII hoặc cập nhật giao diện Cloudflare Edge Dashboard.

---

## Quy trình 4 Bước Triển khai cho Website / Chủ đề mới

### Bước 1: Thiết lập Cấu hình Ngành nghề (`configs/domain.config.json`)
- Không sửa code Python trong `core/`, `processing/`, hay `services/`.
- Nếu lĩnh vực của người dùng khớp với các preset có sẵn trong `presets/`:
  - Đa ngành / Công nghệ / Kinh doanh: sao chép `presets/general-docs.json` -> `configs/domain.config.json`.
  - Pháp lý / Hợp đồng / Biểu mẫu: sao chép `presets/legal-business.json` -> `configs/domain.config.json`.
  - Giáo dục / STEM (cần công thức KaTeX): sao chép `presets/education-stem.json` -> `configs/domain.config.json`.
- Cập nhật mục `brand` trong `configs/domain.config.json`:
  - `name`, `full_name`, `domain`, `public_base_url`, `files_base_url`, `document_route_prefix`, `dashboard_title`, `default_author`.
- Cập nhật mục `taxonomy` (`categories`, `document_types`, `levels`, `frameworks`, `require_formulas_for_categories`).

### Bước 2: Khai báo Nguồn Thu thập (`configs/sources_registry.json`)
- Thêm các nguồn mục tiêu vào mảng `sources` trong `configs/sources_registry.json`:
  - `adapter_type`: `"sitemap"`, `"rss"`, `"blogger_api"`, hoặc `"html_spider"`.
  - `feed_url` / `base_url`: URL của RSS feed hoặc Sitemap XML.
  - `primary_category`: Chuyên mục mặc định khi phân loại.

### Bước 3: Kiểm tra bằng Unit Test Suite
Chạy lệnh kiểm thử để đảm bảo cấu hình mới tương thích 100% với 3 Agent:
```powershell
uv run --with pymupdf --with pillow --with pypdf --with requests --with beautifulsoup4 python -m unittest discover -s tests -p "test_*.py" -v
```

### Bước 4: Kết nối Cloudflare D1 + R2 & Triển khai Edge Dashboard
1. Cấu hình biến môi trường / GitHub Actions Secrets:
   - `CLOUDFLARE_ACCOUNT_ID`
   - `CLOUDFLARE_D1_DATABASE_ID`
   - `CLOUDFLARE_R2_BUCKET`
   - `CLOUDFLARE_API_TOKEN`
   - `DOCUMENT_INGEST_TOKEN`
   - `AG_CLOUD_ENABLED=true`
2. Chạy kiểm tra kết nối an toàn (Preflight):
   ```powershell
   uv run --with requests python services/run_cloud_cycle.py --mode preflight --local-read-only
   ```
3. Triển khai Edge Dashboard (`cloudflare-edge-dashboard/`):
   - Cập nhật `wrangler.jsonc` với `database_id`, `bucket_name`, `routes`, `PORTAL_NAME`, `PORTAL_URL`.
   - Chạy `npx wrangler deploy`.
