# PROJECT IDENTITY
- **Name**: paper-data-etl
- **Objective**: Tạo dữ liệu continual pretraining cho LLM. Thu thập và xử lý các bài báo khoa học Việt Nam từ trang CSDL Quốc Gia (VISTA - sti.vista.gov.vn), tạo ra corpus sạch, chất lượng cao, đồng thời xây dựng bộ báo cáo trực quan để đánh giá dữ liệu.
- **Nguồn dữ liệu**: Đang tập trung 100% vào **VISTA**. Dự án từng thử nguồn VJOL (17-18/08/2026) nhưng đã pivot sang VISTA — chi tiết luồng chảy của cả 2 xem `docs/PIPELINE_VISTA.md` (đang chạy) và `docs/PIPELINE_VJOL.md` (đã lưu trữ).

# TECH STACK
- **Language**: Python 3.11+
- **Package Manager**: `uv` + `requirements.txt`
- **Frameworks/Libraries**:
  - Request handling & crawling: `curl_cffi` (TLS Spoofing bypass WAF), `asyncio` (Overclocking), `BeautifulSoup`
  - Data Processing & Storage: `pandas`, `duckdb`, `pyarrow` (Parquet, JSONL)
  - Document Parsing (mục tiêu, chưa triển khai): `pypdf`, `pymupdf`, local AI OCR (Marker chạy trên 4 GPU A100)
  - Text Normalization: `ftfy`
  - Orchestration (mục tiêu, chưa triển khai): `Ray`
- **Database Systems**: Local file system (Disk-chained stages), DuckDB (Analytics)

# SYSTEM ARCHITECTURE
- `src/discovery/vista_crawler.py`: Discovery + Download bất đồng bộ cho VISTA (quét pagination HTML, tải PDF song song). Đây là code đang chạy thật — chi tiết xem `docs/PIPELINE_VISTA.md`.
- `src/common/logger.py`: Cấu hình log dùng chung.
- `scripts/run_crawler.py`: Entry point chạy crawler VISTA.
- `scripts/benchmark_*.py`, `scripts/test_*.py`, `scripts/generate_sticky_proxies.py`: Thử nghiệm tìm cấu hình proxy/tốc độ tối ưu (chưa merge vào `src/`).
- `src/processing/` (chưa tồn tại): Dự kiến chứa `PDFTriager`/`PDFParser` dùng Ray + GPU để bóc tách text từ PDF — xem lộ trình đầy đủ ở `docs/IMPLEMENTATION_PLAN.md`.
- Cấu trúc chi tiết thư mục `data/` xem `docs/PROJECT_ARCHITECTURE.md`.

# ACTIVE INTEGRATIONS
- **TLS Spoofing & Async Overclock**: Bỏ qua WAF của VISTA bằng TLS Client (`curl_cffi`, impersonate Chrome), gộp chung HTTP request bất đồng bộ.
- **Stage-based disk-chained processing**: Lưu trữ dữ liệu trung gian tại từng bước bằng JSONL/Parquet.
- **Proxy pool tĩnh (`proxies.txt`)**: Thay cho Rotating Gateway để giảm lỗi 429 — xem mục "Đang thử nghiệm" trong `docs/PIPELINE_VISTA.md`.

# DEVELOPMENT LOG (tóm tắt — số liệu benchmark chi tiết xem lịch sử git)
- **2026-08-17**: Khởi tạo dự án, thử nghiệm VJOL (OAI-PMH harvest, tải thành công 20 bài).
- **2026-08-18**: Pivot sang VISTA. Viết crawler `curl_cffi` + `asyncio` để vượt WAF, tăng tốc tải PDF trực tiếp từ trang danh sách (rút thời gian ước tính từ ~24 ngày xuống ~1.1 ngày).
- **2026-08-19**: Benchmark rate limit độc lập VISTA vs VJOL, rồi benchmark sâu proxy pool cho VISTA:
  - Không proxy: VISTA ~70% thành công (nhiều 429), VJOL ~100% thành công.
  - 10 proxy tĩnh: từ 6% (spam liên tục) cải thiện lên 100% khi dùng Rotating Gateway của Webshare (100/100 bài, ~14 phút).
  - Thử 5 policy worker/sleep/backoff khác nhau (10-20 workers): tốt nhất đạt ~8.17 bài/phút, nhưng Rotating Gateway vẫn sinh nhiều lỗi 429 do chọn IP ngẫu nhiên.
  - **Kết luận & hướng đi tiếp theo**: Chuyển sang quản lý proxy tĩnh theo IP (`StatefulProxyManager`, đọc `proxies.txt`) — mỗi IP chỉ được cấp phát lại sau khi nghỉ đủ cooldown 15s của WAF VISTA. Thiết kế này đang ở dạng script thử nghiệm (`scripts/test_stateful_proxy.py`), chưa merge vào `src/discovery/vista_crawler.py`.
