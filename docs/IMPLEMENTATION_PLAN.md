# Kế Hoạch Triển Khai: Target Architecture (Sau Discovery)

> **Lưu ý**: Tài liệu này ban đầu được thiết kế cho nguồn **VJOL** với kiến trúc OAI-first + Ray/GPU (kế thừa từ hệ thống ViLA). Dự án đã pivot nguồn dữ liệu sang **VISTA** (xem `docs/PIPELINE_VISTA.md` cho luồng Discovery + Download đang chạy thật, và `docs/PIPELINE_VJOL.md` cho pipeline VJOL đã lưu trữ). Các stage xử lý downstream (Parse → Package) bên dưới **độc lập với nguồn dữ liệu** và vẫn là mục tiêu kiến trúc cho giai đoạn kế tiếp — nhưng **chưa được triển khai** trong code hiện tại (`src/` mới chỉ có Discovery + Download).

> **Mục tiêu:** Thu thập corpus bài báo khoa học công khai, tạo dữ liệu sạch cho continued pretraining LLM, đồng thời xây bộ báo cáo trực quan để đánh giá độ sạch, đa dạng, cân bằng và độ bao phủ.

## Funnel dữ liệu cần đo lường
```text
publications discovered -> PDF downloaded and verified -> PDF parsed -> scientific structure extracted
-> quality accepted -> deduplicated -> rights approved -> packaged corpus
```

## Công nghệ dự kiến cho các stage downstream
- **PDF & OCR**: `pypdf`/`pymupdf` (baseline nhanh), `GROBID`, `Docling`/`Marker` (layout phức tạp), Local AI OCR (Marker/Nemotron trên 4 GPU A100) cho PDF dạng scan.
- **Orchestration**: `Ray` (chia việc GPU), `UMAP`/`HDBSCAN` (clustering).
- **Visualization**: `Plotly`, `DuckDB`, `Datashader`.

## Các stage đã hoàn thành
- **Discovery + Download**: Đã triển khai cho VISTA — xem `docs/PIPELINE_VISTA.md`.

## Các stage mục tiêu (chưa triển khai)

**Triage & Parse PDF**
- Đánh giá loại PDF trước khi parse: `text_native`, `mixed`, `image_only`, `corrupt`, `protected`, `non_article` (số trang, tỷ lệ text/image, entropy, ngôn ngữ dự đoán).
- Chiến lược "rẻ trước đắt sau": `PyMuPDF`/`GROBID` cho text cơ bản → `Docling`/`Marker` cho layout/bảng phức tạp → Local AI OCR (4 GPU A100 qua Ray) cho PDF dạng scan.
- Output: `raw.md` (để train) + `document.json` (giữ provenance, bounding box).

**Normalize**
- Chuẩn hóa Unicode NFC, nối đoạn bị đứt trang, xóa control char, loại header/footer lặp.
- KHÔNG paraphrase/dịch/sửa nội dung bằng LLM.

**Structure Extraction**
- Map section về chuẩn: `abstract`, `introduction`, `methods`, `results`, `conclusion`, `references`.
- Tách riêng `references` để phân tích citation graph hoặc loại trừ khi train.

**Quality Scoring & Quarantine**
- Chấm điểm theo: Completeness (tiêu đề/tác giả/abstract), toàn vẹn văn bản (tỷ lệ lỗi ký tự, OCR confidence), tính khoa học (không phải bìa tạp chí, body hợp lý).
- Quality bands: `A` (train-ready), `B` (thiếu metadata phụ), `C` (giữ để sửa), `D` (bỏ), `R` (giam do bản quyền).

**Deduplication**
- Exact: `PDF SHA-256`, `normalized_text_hash`, `DOI`.
- Near-dedup: MinHash/SimHash, tiêu đề + năm.
- Giữ các cụm bản dịch (Anh–Việt) cùng một data split để tránh rò rỉ train/validation.

**Classification & Balance**
- Map lĩnh vực vào taxonomy chuẩn (OECD/OpenAlex).
- Đo cân bằng theo lĩnh vực, ngôn ngữ, tạp chí, chất lượng — tránh một tạp chí áp đảo corpus.

**Rights Gate**
- Chỉ đưa vào Train Release khi đạt chuẩn kỹ thuật VÀ có quyền sử dụng (`permission_granted` hoặc open license); thiếu bản quyền → `rights_quarantine`.

**Package & Visualize**
- Format: Parquet (phân tích) + `.jsonl.zst` (lưu trữ). Không chia Train/Val/Test ở bước này.
- Views: `full_document`, `body_only`, `abstract_only`.
- Embedding (Title+Abstract, Body) → UMAP/HDBSCAN để tìm khoảng trống dữ liệu, cụm parse lỗi, bias ngôn ngữ.
- Dashboard (DuckDB + Plotly): coverage funnel, missingness heatmap, balance map, rights/quality distribution.

**Incremental Update**
- Harvest định kỳ record mới; release cũ không bị ghi đè, mỗi lần update có release manifest riêng.

## Lời khuyên triển khai
Test toàn bộ pipeline (Discovery → Package) với một tập nhỏ đại diện trước khi chạy full-scale trên cluster GPU. Bài không có PDF (`abstract_only`) vẫn được parse và đóng gói như một view riêng.
