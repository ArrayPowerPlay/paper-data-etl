# Kế Hoạch Triển Khai: VJOL Paper Data ETL

Xây dựng một Data Pipeline (ETL) để thu thập, xử lý và chuẩn hóa các bài báo khoa học trên Vietnam Journals Online (VJOL), tạo ra một corpus sạch phục vụ cho quá trình continued pretraining của LLM. 
Hệ thống áp dụng kiến trúc stage-based disk chaining, polite session, parser triage, tận dụng sức mạnh tính toán song song từ Ray và 4 GPU A100.

---

### Phase 1: Core Infrastructure & Discovery (Stages 00 - 02)

Xây dựng nền tảng pipeline và công cụ crawl OAI-PMH.

- **Tasks**:
  - Khởi tạo project (`uv`, `requirements.txt`, folder structure).
  - Cấu hình `Ray local cluster` tối ưu cho máy 1 node (4 GPU A100).
  - Viết `PoliteSession` (Rate limiting, retry backoff, tuân thủ `robots.txt`).
  - Viết `OAIHarvester`: Preflight check, ListSets, ListRecords.
- **Testcases**:
  - `test_polite_session`, `test_oai_harvester_pagination`, `test_xml_parsing_safety`.

### Phase 2: Metadata Canonicalization & Enrichment (Stages 03 - 05)

Chuẩn hóa metadata và tải PDF.

- **Tasks**:
  - `Canonicalizer`: Chuyển OAI Dublin Core XML thành JSONL.
  - `HTMLEnricher`: Trích xuất metadata từ thẻ HTML meta cho các bài thiếu thông tin.
  - `PDFDownloader`: Tải PDF, có tùy chọn `streaming & cleanup` (tự động xóa PDF sau khi xử lý xong để tiết kiệm ổ cứng), check SHA-256.
- **Testcases**:
  - `test_canonicalize_multi_lang`, `test_pdf_magic_bytes`, `test_downloader_resume`.

### Phase 3: PDF Triage, Parsing & Normalization (Stages 06 - 08)

Phân loại và bóc tách nội dung văn bản từ PDF (sử dụng GPU Acceleration).

- **Tasks**:
  - `PDFTriage`: Phân loại PDF (native text, scan, corrupt, v.v.).
  - `DocumentParser`: Pipeline phân tách văn bản.
    - Native Text: Dùng `PyMuPDF/pypdf`.
    - Image/Scan: Giao phó cho Ray Actors xử lý bằng mô hình local OCR chuyên khoa học (như Marker/Nougat/Surya) chạy trên 4 GPU A100 (miễn phí, chất lượng cao).
  - `Normalizer`: Xử lý Unicode NFC, dehyphenation.
- **Testcases**:
  - `test_pdf_triage_image_only`, `test_unicode_nfc_normalization`, `test_parser_extracts_blocks`.

### Phase 4: Structure Extraction & Quality Scoring (Stages 09 - 10)

Trích xuất cấu trúc khoa học và chấm điểm dữ liệu.

- **Tasks**:
  - `ScientificExtractor`: Tách Title, Abstract, Introduction, References...
  - `QualityScorer`: Phân loại A, B, C, D.
- **Testcases**:
  - `test_extract_references`, `test_quality_scorer_band_d`.

### Phase 5: Deduplication & Train Packaging (Stages 11 - 14)

Loại bỏ bản sao và đóng gói corpus.

- **Tasks**:
  - `Deduplicator`: Lọc trùng lặp (SHA-256, MinHash).
  - `RightsGate`: Phân loại bản quyền (`training_eligible`).
  - `Packager`: Chia Train/Validation/Test. Xuất Parquet/JSONL.
- **Testcases**:
  - `test_exact_deduplication`, `test_train_val_leakage`.

### Phase 6: Analytics & Visualization (Stages 15 - 16)

Trực quan hóa độ phủ, đa dạng và phân bổ của corpus.

- **Tasks**:
  - `TextEmbedder` & `Reducer`: Tận dụng 4 GPU A100 để sinh embedding siêu tốc, giảm chiều UMAP.
  - `Dashboard`: Dùng DuckDB và Plotly tạo `paper_dashboard.html`.
- **Testcases**:
  - `test_duckdb_aggregations`.
