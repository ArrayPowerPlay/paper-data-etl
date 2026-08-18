import asyncio
import argparse
from src.discovery.vista_crawler import VistaCrawler
from src.common.logger import setup_logger

logger = setup_logger(__name__)

def run_pipeline(start_page, end_page):
    logger.info(f"Khởi động tiến trình VISTA Crawler từ trang {start_page} đến {end_page}")
    crawler = VistaCrawler(total_pages=end_page)
    asyncio.run(crawler.run_overclocked_pipeline(start_page=start_page, end_page=end_page))
    logger.info("Hoàn tất tiến trình Crawl.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chạy riêng biệt tiến trình Crawl & Tải PDF")
    parser.add_argument("--start-page", type=int, default=0, help="Trang bắt đầu (mặc định: 0)")
    parser.add_argument("--end-page", type=int, default=22500, help="Trang kết thúc (mặc định: 22500 trang ~ 450,000 bài)")
    args = parser.parse_args()
    
    run_pipeline(args.start_page, args.end_page)
