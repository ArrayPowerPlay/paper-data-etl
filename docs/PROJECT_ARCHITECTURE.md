# Cấu Trúc Dự Án (Project Architecture)

Tài liệu này giải thích ý nghĩa các thư mục/file chính trong repo. Chi tiết luồng chạy xem `docs/PIPELINE_VISTA.md` (đang triển khai) và `docs/PIPELINE_VJOL.md` (đã lưu trữ).

## 1. Mã nguồn
- **`src/common/logger.py`**: Cấu hình log dùng chung.
- **`src/discovery/vista_crawler.py`**: Toàn bộ logic Discovery + Download của VISTA (`curl_cffi` + `asyncio` để vượt WAF).
- **`scripts/run_crawler.py`**: Entry point chạy crawler VISTA (`--start-page`, `--end-page`).
- **`scripts/benchmark_*.py`, `scripts/test_*.py`, `scripts/generate_sticky_proxies.py`**: Script thử nghiệm/benchmark cấu hình proxy & tốc độ crawl, chưa merge vào `src/`.
- **`src/processing/`**: Chưa tồn tại — dự kiến chứa logic Ray + GPU (Marker OCR) để bóc tách text từ PDF (xem `docs/IMPLEMENTATION_PLAN.md`).

## 2. Thư mục dữ liệu (`data/`)
Kiến trúc **Disk-chained**: làm đến đâu lưu ra đĩa đến đó để chống crash và có thể resume.

### Các file điều phối
- **`data/discovery_queue.jsonl`**: Hàng chờ — mỗi bài quét được từ trang danh sách VISTA (ID, tiêu đề, link tải) được ghi vào đây trước khi tải.
- **`data/downloaded_log.jsonl`**: Sổ ghi kết quả tải — mỗi bài xử lý xong (`downloaded`/`corrupt_pdf`/`download_failed`) được append vào đây. Khi khởi động lại, crawler đọc file này đầu tiên để **bỏ qua (dedupe)** các bài đã tải thành công.

### Thư mục PDF
- **`data/raw/pdf/`**: File PDF gốc tải từ VISTA, đặt tên theo `SHA-256` để loại trừ file trùng nội dung.

### Thư mục thử nghiệm (không phải dữ liệu chính thức)
- **`data/policy_benchmarks/`, `data/vista_benchmark_100/`, `data/vista_optimized_100/`, `data/vista_rotating_100/`, `data/proxy_test_download/`, `data/stateful_proxy_test/`**: Output của các script benchmark proxy/tốc độ trong `scripts/`, dùng để so sánh policy chứ không phải corpus thu thập chính thức.

### Còn lại từ thử nghiệm VJOL (lịch sử, không còn cập nhật)
- **`data/vjol_temp/`**: Dữ liệu tạm từ lần chạy thử VJOL — xem `docs/PIPELINE_VJOL.md`.

## 3. Tệp cấu hình
- **`proxies.txt`**: Danh sách proxy tĩnh định dạng `IP:PORT:USERNAME:PASSWORD`, dùng cho thử nghiệm `StatefulProxyManager`.
- **`.env`** (không commit): Biến `PROXIES` — danh sách proxy phân tách bởi dấu phẩy, dùng bởi `src/discovery/vista_crawler.py`.

## Tóm lược luồng chạy chính thức (VISTA)
1. Khởi chạy `PYTHONPATH="." python scripts/run_crawler.py` (mặc định quét đến hết danh sách).
2. Crawler đọc `data/downloaded_log.jsonl` để né các bài đã tải.
3. Quét trang danh sách VISTA, ghi metadata vào `data/discovery_queue.jsonl`.
4. Các worker song song tải PDF, lưu vào `data/raw/pdf/<SHA-256>.pdf`.
5. Ghi kết quả vào `data/downloaded_log.jsonl`.

Xem `docs/PIPELINE_VISTA.md` để có sơ đồ chi tiết từng bước.
