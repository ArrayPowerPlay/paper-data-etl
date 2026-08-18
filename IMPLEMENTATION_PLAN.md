# Kế Hoạch Triển Khai: VJOL Paper Data ETL (Detailed)

> **Mục tiêu:** Thu thập corpus bài báo khoa học công khai trên Vietnam Journals Online (VJOL), tạo dữ liệu sạch cho continued pretraining LLM, đồng thời xây bộ báo cáo trực quan để đánh giá độ sạch, đa dạng, cân bằng và độ bao phủ.
> 
> Bản thiết kế này kế thừa toàn bộ kinh nghiệm và kiến trúc từ hệ thống **ViLA**, áp dụng pipeline **OAI-first hybrid** kết hợp xử lý song song bằng **Ray** trên 4 GPU A100.

---

## 1. Kiến trúc Tổng Quan

Pipeline gồm 17 Stages, được thiết kế theo cơ chế **Stage-based disk chaining** (mỗi bước đọc output từ đĩa của bước trước và ghi artifact mới). Điều này giúp dễ dàng resume, debug và không cần chạy lại toàn bộ pipeline khi xảy ra lỗi.

### Funnel Dữ Liệu Cần Đo Lường
```text
journals discovered -> OAI records harvested -> article records valid -> public full text discovered -> PDF downloaded and verified -> PDF parsed -> scientific structure extracted -> quality accepted -> deduplicated -> rights approved -> assigned to train/validation/test
```

### Công Nghệ
- **Core**: Python 3.11+, `uv` (dependency management)
- **Crawl & HTTP**: `requests`, `lxml` (XML parser namespace-aware), `PoliteSession` (TokenBucket rate limiter)
- **Data Processing**: `pandas`, `duckdb`, `pyarrow` (Parquet, JSONL)
- **PDF & OCR**: `pypdf`/`pymupdf` (baseline), `GROBID`, `Docling`/`Marker`, Local OCR models (Nemotron/Marker chạy trên 4 GPU A100)
- **Orchestration & Reduce**: `Ray` (multi-processing), `UMAP`/`HDBSCAN`
- **Visualization**: `Plotly`, `Datashader`

---

## 2. Chi Tiết Các Giai Đoạn (Stages 00 - 17)

### Phase 1: Core Infrastructure & Discovery (VISTA Asynchronous TLS Spoofing Strategy)
**Stage 00 - Preflight & Bypassing WAF**
- Trang sti.vista.gov.vn chặn bot truyền thống bằng WAF (Application Firewall Alert).
- Giải pháp: Sử dụng thư viện **`curl_cffi`** kết hợp **`asyncio`** để giả lập TLS fingerprint của Google Chrome. Việc này giúp bypass WAF nhẹ nhàng mà không cần mở trình duyệt, cấu hình mức độ ép xung (Overclock) để chạy song song.

**Stage 01 - Discover Publications (HTML Pagination)**
- Chạy vòng lặp bất đồng bộ quét các trang danh sách: `https://sti.vista.gov.vn/?mod=publication&page=<offset>`.
- Parse bằng `BeautifulSoup` để tự động extract các thẻ thông tin bài báo (Title) và đặc biệt là **link tải PDF lộ thiên** trên thẻ (VD: `/publication/download/...`).
- Lưu toàn bộ danh sách metadata và link tải vào `discovery_queue.parquet`. Không cần vào xem trang chi tiết bài báo, giúp tiết kiệm 1/3 số lượng request.

### Phase 2: PDF Verification & Download
**Stage 02 - Overclocked PDF Download (Bất đồng bộ)**
- Đẩy danh sách link từ `discovery_queue.parquet` vào một `asyncio.Queue`.
- Khởi tạo Pool gồm 5-10 workers (cùng dùng `curl_cffi`) để kéo PDF song song với tốc độ tổng hợp khoảng 5 request/s.
- Kiểm tra tính hợp lệ bằng Magic bytes (`%PDF`). Lọc bỏ file HTML rác bị tường lửa chặn lại (nếu có).
- Lưu file PDF băm theo thuật toán `SHA-256` để deduplicate ngay từ bước tải. Đẩy đường dẫn PDF hợp lệ vào thư mục `data/raw/pdf`.

**Stage 03 - Điều phối luồng xử lý (Stream Handoff)**
- Sẵn sàng kích hoạt các GPU Ray Worker của Phase 3 để bóc tách text ngay khi file PDF vừa đáp xuống đĩa cứng.

### Phase 3: PDF Triage, Parsing & Normalization
**Stage 06 - PDF Triage**
- Đánh giá PDF trước khi parse: `text_native`, `mixed`, `image_only`, `corrupt`, `protected`, `non_article`.
- Tính metrics: số trang, tỷ lệ text/image, entropy, ngôn ngữ dự đoán.

**Stage 07 - Parse PDF thành Cấu trúc (Tận dụng GPU A100)**
- Áp dụng chiến lược "rẻ trước đắt sau":
  - Dùng parser nhanh (`PyMuPDF`) hoặc `GROBID` cho metadata/text cơ bản.
  - Phân tích layout phức tạp (Markdown, bảng) bằng `Docling`/`Marker`.
  - Fallback sang **Local AI OCR** (chạy phân tán trên 4 GPU A100 qua Ray) cho các PDF dạng scan (`image_only`, `mixed`).
- Lưu 2 định dạng output: `raw.md` (để train) và `document.json` (giữ provenance, bounding box).

**Stage 08 - Normalize an toàn cho học thuật**
- Chuẩn hóa encoding (Unicode NFC), nối đoạn bị đứt trang, xóa control char, loại bỏ header/footer bị lặp.
- KHÔNG paraphrase, dịch thuật, sửa tên, hay thay đổi nội dung nguyên bản bằng LLM.

### Phase 4: Structure Extraction & Quality Scoring
**Stage 09 - Trích xuất cấu trúc bài báo**
- Mapping các section bề mặt về chuẩn: `abstract`, `introduction`, `methods`, `results`, `conclusion`, `references`...
- Tách riêng `references` để phân tích đồ thị trích dẫn (citation graph) hoặc để loại trừ lúc huấn luyện.

**Stage 10 - Data Quality Scoring & Quarantine**
- Chấm điểm chất lượng theo nhiều trục:
  - Tính toàn vẹn (Completeness): có tiêu đề, tác giả, abstract...
  - Toàn vẹn văn bản: tỷ lệ ký tự lỗi, OCR confidence.
  - Tính khoa học: không phải bìa tạp chí, có body hợp lý.
- Quality bands: `A` (train-ready), `B` (usable nhưng thiếu metadata phụ), `C` (giữ để sửa), `D` (bỏ), `R` (bị giam do bản quyền).

### Phase 5: Deduplication, Classification & Rights Gate
**Stage 11 - Deduplication (Loại bỏ trùng lặp)**
- Trùng lặp chính xác: `PDF SHA-256`, `normalized_text_hash`, `DOI`.
- Trùng lặp gần (Near-dedup): MinHash/SimHash, tiêu đề + năm.
- Giữ các cụm bản dịch (Ví dụ bản Anh - Việt) vào cùng một data split (để không bị lọt thông tin giữa train/validation).

**Stage 12 - Phân loại lĩnh vực (Classification & Balance)**
- Map lĩnh vực vào taxonomy chuẩn (OECD / OpenAlex).
- Đo độ cân bằng về lĩnh vực, ngôn ngữ, tạp chí, chất lượng, loại tài liệu. Tránh tình trạng một tạp chí áp đảo toàn corpus.

**Stage 13 - Rights Gate (Quản trị bản quyền)**
- Đánh giá Training Eligibility: Dữ liệu chỉ được đưa vào Train Release khi đạt chuẩn kỹ thuật VÀ có quyền sử dụng (`permission_granted` hoặc open license).
- Nếu thiếu bản quyền: Phân loại vào `rights_quarantine`.

### Phase 6: Packaging, Embedding & Visualization
**Stage 14 - Đóng gói Corpus (Package)**
- Format: Parquet (phân tích) và `.jsonl.zst` nén (lưu trữ).
- Dữ liệu đầu ra là một corpus thống nhất, không chia tập Train/Test/Val ở bước này (việc chia tập sẽ do pipeline huấn luyện mô hình đảm nhiệm).
- Các góc nhìn (Views): `full_document`, `body_only`, `abstract_only` (cho các bài `missing_pdf_url`).

**Stage 15 - Embedding, Giảm chiều & Clustering**
- Embed Title + Abstract, Body sections bằng mô hình đa ngữ.
- Giảm chiều dữ liệu (PCA/UMAP trên sample) và cluster bằng HDBSCAN.
- Mục đích: Tìm khoảng trống dữ liệu, tìm cụm parse lỗi, kiểm tra bias ngôn ngữ (KHÔNG phục vụ RAG).

**Stage 16 - Visualization (Dashboard Audit)**
- Trực quan hóa bằng DuckDB + Plotly:
  - *Coverage funnel*: Theo dõi lượng sụt giảm từ lúc OAI phát hiện đến khi đóng gói.
  - *Missingness heatmap*: Các trường bị thiếu theo từng journal.
  - *Balance & Semantic Map*: Bản đồ UMAP thể hiện lĩnh vực/ngôn ngữ.
  - *Rights & Quality distribution*.

**Stage 17 - Incremental Update**
- Vận hành định kỳ. Tự động `harvest` các record mới thông qua tham số thời gian (`from`).
- Các release cũ không bị ghi đè, tạo release manifest cho lần update mới.

---
## Lời Khuyên Triển Khai Thực Tế
Thực hiện theo chiến lược **Vertical Slice**: Test toàn bộ 17 Stages với 5-10 journal đại diện (Tiếng Việt/Anh, Tự nhiên/Xã hội, Cũ/Mới) trước khi cho cluster GPU chạy full-text toàn hệ thống VJOL. Dữ liệu `abstract_only` (không có PDF) vẫn sẽ được parse và package như một view riêng lẻ.
