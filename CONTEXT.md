# PROJECT IDENTITY
- **Name**: paper-data-etl
- **Objective**: Tạo dữ liệu continual pretraining cho LLM. Thu thập và xử lý các bài báo khoa học Việt Nam từ trang Vietnam Journals Online (VJOL - vjol.info.vn), tạo ra corpus sạch, chất lượng cao, đồng thời xây dựng bộ báo cáo trực quan để đánh giá dữ liệu.

# TECH STACK
- **Language**: Python 3.11+
- **Package Manager**: `uv` + `requirements.txt`
- **Frameworks/Libraries**:
  - Request handling & crawling: `requests`, `lxml` / `defusedxml` (OAI-PMH parsing)
  - Data Processing & Storage: `pandas`, `duckdb`, `pyarrow` (Parquet, JSONL)
  - Document Parsing: `pypdf`, `pymupdf` (baseline), local AI OCR (Marker / Surya / Nougat chạy trực tiếp trên GPU A100).
  - Text Normalization: `ftfy`
  - Visualization: `plotly`, `datashader`
  - Orchestration: `Ray` (Sử dụng Ray local cluster để điều phối tải cho 4 GPU A100 40GB).
- **Database Systems**: Local file system (Disk-chained stages), DuckDB (Analytics)

# SYSTEM ARCHITECTURE
- `<project_root>/`
  - TBD: Cấu trúc thư mục sẽ được định hình chi tiết sau khi kế hoạch được phê duyệt. Hệ thống sẽ tuân theo kiến trúc Stage-based pipeline.

# ACTIVE INTEGRATIONS
- **ViLA Architecture Patterns**:
  - **Stage-based disk-chained processing**: Lưu trữ dữ liệu trung gian tại từng bước.
  - **PoliteSession**: Tích hợp Token bucket rate-limiter, cơ chế retry với backoff để bảo vệ server VJOL.
  - **Deterministic Pipeline**: Các bước xử lý sử dụng cơ chế cache key xác định để đảm bảo reproducible outputs.
  - **Ray Orchestration & GPU Acceleration**: Tận dụng Ray Actors để chia nhỏ pipeline và xử lý OCR/Embedding song song qua 4 GPU A100.
  - **Storage Auto-cleanup**: (Tùy chọn) Xóa PDF ngay sau khi parse xong để tiết kiệm ổ cứng.

# DEVELOPMENT LOG
- **2026-08-17**: Khởi tạo dự án. Phân tích tài liệu kiến trúc. Chốt phương án kỹ thuật: dùng uv, tích hợp Ray để tận dụng 4xA100 GPU, và dùng local AI OCR (miễn phí).
