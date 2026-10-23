# 📋 HỒ SƠ BÀN GIAO CÔNG NGHỆ LÕI: AG DOC-ENGINE CORE v3.0

## 1. Mục đích của Bản Bàn Giao này
Tài liệu này giúp chủ sở hữu dự án (**anh Hiếu**) và bất kỳ phiên **Antigravity (AGY)** nào mở thư mục `D:\AG-DocEngine-Core` (hoặc fork từ GitHub Template `nguyenduchieu0310-dot/ag-doc-engine-core`) nắm bắt ngay kiến trúc và nhân bản hệ thống sang một website mới chỉ trong **1 câu lệnh duy nhất**.

---

## 2. Những gì đã được Chuẩn hóa & Tách biệt khỏi Dự án Gốc

| Thành phần | Ở dự án gốc (`Beekip`) | Ở Công nghệ lõi (`AG DocEngine Core v3.0`) |
| :--- | :--- | :--- |
| **Thương hiệu & Domain** | Cố định `Beekip`, `tailieu.beekip.vn` | Động 100% qua `configs/domain.config.json` (`brand.name`, `brand.public_base_url`) |
| **Chủ đề & Phân loại** | Cố định Toán, Lý, Hóa, Lớp 10-12, GDPT 2018 | Động 100% qua `taxonomy` (`categories`, `levels`, `document_types`, `frameworks`) |
| **Kiểm tra công thức KaTeX** | Bắt buộc cho các môn tự nhiên | Tùy chọn theo danh mục qua `require_formulas_for_categories` (Tắt cho Văn bản/Pháp lý/Kinh doanh; Bật cho STEM) |
| **Bố cục bài viết 4 phần** | Cố định tiêu đề H2 ôn thi/đề thi | Tùy biến cả 4 tiêu đề H2 và nhãn phụ lục qua `article_template` trong `domain.config.json` |
| **Bảng D1 Queue & Logs** | `beekip_crawler_queue` | Chuẩn hóa thành `ag_crawler_queue`, `ag_crawler_sources`, `ag_crawler_blobs` |
| **3 Preset mẫu dựng sẵn** | Không có | Có sẵn `general-docs.json`, `legal-business.json`, `education-stem.json` |

---

## 3. Câu lệnh Prompt Mẫu để Giao việc cho AGY ở Dự án Mới

Khi anh mở thư mục dự án mới (đã clone/fork từ `ag-doc-engine-core`) trên một cửa sổ AGY mới, anh chỉ cần nhắn cho AGY câu lệnh sau:

> **Prompt mẫu:**
> *"Em đọc `AGENTS.md`, `CORE_ENGINE_HANDOVER_SPEC.md` và kỹ năng `ag-doc-engine-core` trong dự án này nhé. Anh muốn áp dụng công nghệ AG DocEngine Core v3.0 này cho website mới là `[TÊN_MIỀN_MỚI]` về chủ đề `[CHỦ_ĐỀ_MỚI, ví dụ: Hợp đồng & Văn bản Pháp lý / Tài liệu Y khoa / Báo cáo Tài chính]`. Hãy cấu hình `configs/domain.config.json`, thiết lập nguồn cào trong `configs/sources_registry.json`, chạy pass toàn bộ Unit Tests và chuẩn bị sẵn cấu hình Cloudflare D1/R2 cho anh!"*
