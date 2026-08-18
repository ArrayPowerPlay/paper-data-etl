# Cấu Trúc Dự Án (Project Architecture)

Tài liệu này giải thích chi tiết ý nghĩa của các thư mục và file sinh ra trong quá trình chạy Pipeline VISTA Crawler.

## 1. Thư mục mã nguồn (`src/`)
Toàn bộ code logic của hệ thống nằm ở đây.
- **`src/common/`**: Chứa các file cấu hình dùng chung như module log (`logger.py`).
- **`src/discovery/`**: Chứa code lùng sục dữ liệu. File `vista_crawler.py` đóng vai trò rà quét toàn bộ trang danh sách của VISTA để bóc tách siêu dữ liệu và link PDF (sử dụng thư viện `curl_cffi` và `asyncio` để vượt WAF).
- **`src/processing/`** (Sắp tới): Nơi chứa logic dùng Ray và GPU (Marker OCR) để bóc tách text từ file PDF.

## 2. Thư mục chứa Dữ Liệu (`data/`)
Đây là kho chứa toàn bộ chiến lợi phẩm. Hệ thống dùng kiến trúc **Disk-chained** (Làm đến đâu lưu ra đĩa đến đó để chống crash).

### A. Các File Điều Phối (Điều khiển tải ngắt quãng và phân tán)
- **`data/discovery_queue.jsonl`**: Hàng chờ (Queue). Khi crawler quét qua các trang danh sách, nó lưu tạm thông tin bài báo (ID, Tiêu đề, Link tải) vào đây. Luồng tải PDF sẽ đọc từ file này để tải.
- **`data/downloaded_log.jsonl`**: Cuốn sổ Nam Tào. Mỗi khi 1 file PDF được tải và lưu thành công, kết quả được ghi nhận vào đây. Bất cứ khi nào bạn bật lại code, hệ thống sẽ đọc cuốn sổ này đầu tiên để tự động **Bỏ qua (Deduplicate)** những bài đã tải, không bao giờ tải trùng lại.

### B. Các Thư Mục Dữ Liệu Chuyên Dụng
- **`data/raw/pdf/`**: Đích đến cuối cùng của luồng Crawler hiện tại. Nơi chứa toàn bộ file PDF gốc tải từ VISTA. Các file ở đây được đặt tên bằng mã băm `SHA-256` để loại trừ hoàn toàn các file PDF nội dung giống hệt nhau.

## Tóm Lược Luồng Chảy Của VISTA
1. Khởi chạy `$env:PYTHONPATH="."; python scripts/run_crawler.py` (Mặc định sẽ tự chạy toàn bộ trang).
2. Crawler đọc `data/downloaded_log.jsonl` để né các bài đã tải.
3. Kịch bản quét VISTA, đẩy task metadata vào `data/discovery_queue.jsonl`.
4. Băng chuyền 2 luồng (hoặc 5 luồng nếu ép xung mạnh) tải thẳng file PDF về nhét vào `data/raw/pdf/<Mã_SHA256>.pdf`.
5. Đóng mộc thành công vào `data/downloaded_log.jsonl`.
