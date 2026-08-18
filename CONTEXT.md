# PROJECT IDENTITY
- **Name**: paper-data-etl
- **Objective**: Tạo dữ liệu continual pretraining cho LLM. Thu thập và xử lý các bài báo khoa học Việt Nam từ trang CSDL Quốc Gia (VISTA - sti.vista.gov.vn), tạo ra corpus sạch, chất lượng cao, đồng thời xây dựng bộ báo cáo trực quan để đánh giá dữ liệu.

# TECH STACK
- **Language**: Python 3.11+
- **Package Manager**: `uv` + `requirements.txt`
- **Frameworks/Libraries**:
  - Request handling & crawling: `curl_cffi` (TLS Spoofing bypass WAF), `asyncio` (Overclocking), `BeautifulSoup`
  - Data Processing & Storage: `pandas`, `duckdb`, `pyarrow` (Parquet, JSONL)
  - Document Parsing: `pypdf`, `pymupdf` (baseline), local AI OCR (Marker chạy trực tiếp trên 4 GPU A100).
  - Text Normalization: `ftfy`
  - Orchestration: `Ray` (Sử dụng Ray local cluster để điều phối tải cho GPU A100 40GB).
- **Database Systems**: Local file system (Disk-chained stages), DuckDB (Analytics)

# SYSTEM ARCHITECTURE
- `<project_root>/`
  - `src/discovery/`: Quét danh sách bài báo qua pagination HTML bằng `curl_cffi`.
  - `src/enrichment/`: Tải trực tiếp PDF siêu tốc (Overclocked asyncio downloader).
  - `src/processing/`: `PDFTriager` và `PDFParser` sử dụng Ray Actor để chia việc cho 4 GPU.

# ACTIVE INTEGRATIONS
- **TLS Spoofing & Async Overclock**: Bỏ qua WAF của VISTA bằng TLS Client, gộp chung HTTP request bất đồng bộ để đạt giới hạn 5 req/s.
- **Stage-based disk-chained processing**: Lưu trữ dữ liệu trung gian tại từng bước bằng Parquet.
- **Ray Orchestration & GPU Acceleration**: Tận dụng Ray Actors để chia nhỏ pipeline và xử lý OCR song song.

# DEVELOPMENT LOG
- **2026-08-17**: Khởi tạo dự án, phân tích rate limit của VJOL.
- **2026-08-18**: Xoay trục (Pivot) sang VISTA (`sti.vista.gov.vn`). Thiết kế lại Crawler dùng `curl_cffi` và `asyncio` để vượt tường lửa WAF và ép xung tốc độ tải PDF trực tiếp từ trang danh sách (Rút ngắn thời gian từ 24 ngày xuống ~1.1 ngày).
