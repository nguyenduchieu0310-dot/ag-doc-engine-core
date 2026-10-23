# AG DOC-ENGINE CORE v3.0: AGENTS GUIDELINES & SPECIFICATION

## 1. NGUYÊN TẮC QUYẾT ĐỊNH TỰ ĐỘNG (AUTONOMOUS EXECUTION)
1. **Ủy quyền toàn diện**: Người dùng thiết lập nguyên tắc: **"Cho Gemini tự chọn phương án mà Gemini cho là tối ưu nhất"**.
2. **Không hỏi lại các quyết định kỹ thuật**: Tuyệt đối không dừng lại để hỏi xác nhận các lựa chọn kỹ thuật qua `ask_question`. Tự chọn và thực thi ngay phương án tối ưu nhất.
3. **100% Domain-Agnostic (Độc lập Chủ đề & Thương hiệu)**:
   - Tuyệt đối KHÔNG hardcode tên thương hiệu, tên miền hay từ khóa ngành nghề vào mã nguồn Python trong `core/`, `processing/`, `services/`, `cloudflare/`.
   - Mọi thông tin Thương hiệu, Domain, Chuyên mục (`categories`), Phân nhóm (`levels`), Loại tài liệu (`document_types`), Khung tiêu chuẩn (`frameworks`) và Bố cục bài viết 4 phần (`article_template`) đều được cấu hình tập trung tại [`configs/domain.config.json`](file:///D:/AG-DocEngine-Core/configs/domain.config.json) (hoặc nạp từ thư mục [`presets/`](file:///D:/AG-DocEngine-Core/presets/)).

---

## 2. KIẾN TRÚC 3-AGENT KHÉP KÍN (`AG DOC-ENGINE CORE v3.0`)
1. **Agent 0 — Omni-Crawler & Delta Discovery (`adapters/` + `services/omni_scheduler.py`)**:
   - Quét tự động 24/7 qua Sitemap XML, RSS/Atom Feed, Blogger JSON API và HTML Spider.
   - Chặn 100% tệp ảnh tĩnh (`.jpg`, `.png`, `.webp`) và trang HTML rác; chỉ thu nạp **PDF, Word (`.doc/.docx`), PowerPoint (`.ppt/.pptx`)**.
   - Lọc độ tươi mới qua `TemporalYearGuard` (`min_eligible_year` cấu hình trong `configs/domain.config.json`).
2. **Agent 1 — Data & Content Processor (`services/agent_content_processor.py`)**:
   - **Deep Sanitizer (`services/sanitizer.py`)**: Xóa sạch 100% SĐT, Zalo, email cá nhân, watermark chéo, link quảng cáo/VIP của bên thứ ba; bảo toàn 100% hình vẽ, bảng biểu và tên cơ quan/đơn vị phát hành gốc (E-E-A-T).
   - **HD Cover Renderer (`services/derivative_renderer.py`)**: Kết xuất ảnh bìa trang đầu chuẩn Google Discover (`width >= 1200px`, dung lượng `<= 250 KiB`).
   - **4-Section SEO/GEO Content & Dual Schema**: Trích xuất văn bản thật từ từng trang PDF để biên tập bài viết Markdown 4 phần và JSON-LD (`LearningResource`/`DigitalDocument` + `NewsArticle`).
3. **Agent 2 — QA & SEO Sentinel (`services/agent_qa_sentinel.py`)**:
   - Đóng vai trò **Independent Critic** chấm điểm 10 Cổng kiểm định (4 trụ cột: SEO, GEO/E-E-A-T, Google Discover, Safety/Zero-PII).
   - **Cơ chế Tự chữa lành (Self-Healing Loop)**: Nếu điểm `< 100/100`, trả phiếu lỗi (`defects`) về Agent 1 tự động sửa chữa (tối đa 2 vòng) trước khi cho phép xuất bản.
4. **Agent 3 — Auto-Publisher & Indexer (`services/agent_auto_publisher.py` + `cloudflare/`)**:
   - Tải tệp PDF sạch & ảnh bìa HD lên Cloudflare R2, ghi metadata vào Cloudflare D1 (hoặc Ingest API), và ping Google Indexing / IndexNow.
5. **Cloudflare Edge Dashboard (`cloudflare-edge-dashboard/`)**:
   - Trung tâm điều khiển & quan sát 24/7/365 chạy trên Cloudflare Workers (`AG DOC-ENGINE CORE v3.0`).

---

## 3. QUY TRÌNH NHÂN BẢN CHO WEBSITE / CHỦ ĐỀ MỚI (1-COMMAND ONBOARDING)
Khi người dùng yêu cầu áp dụng `AG DocEngine Core v3.0` cho một website hoặc lĩnh vực mới:
1. Chọn preset gần nhất trong `presets/` (`general-docs.json`, `legal-business.json`, `education-stem.json`) hoặc tạo cấu hình mới và ghi vào `configs/domain.config.json`.
2. Cập nhật danh sách nguồn cào (`sources`) trong `configs/sources_registry.json`.
3. Cập nhật thông tin kết nối Cloudflare D1 & R2 trong biến môi trường hoặc `cloudflare-edge-dashboard/wrangler.jsonc`.
4. Chạy bộ kiểm thử tự động:
   ```powershell
   uv run --with pymupdf --with pillow --with pypdf --with requests --with beautifulsoup4 python -m unittest discover -s tests -p "test_*.py" -v
   ```
