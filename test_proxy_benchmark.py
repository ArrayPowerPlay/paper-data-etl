import asyncio
import time
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.discovery.vista_crawler import VistaCrawler
from src.common.logger import setup_logger

logger = setup_logger(__name__)

async def benchmark_100_papers():
    # Sử dụng 10 workers tương ứng với 10 proxies
    crawler = VistaCrawler(output_dir="data", max_concurrent_requests=10)
    
    logger.info("BẮT ĐẦU BENCHMARK TẢI 100 BÀI BÁO (5 TRANG)...")
    start_time = time.time()
    
    # Run pipeline from page 0 to 4 (5 pages = ~100 items)
    await crawler.run_overclocked_pipeline(start_page=0, end_page=5)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    logger.info("="*40)
    logger.info("KẾT QUẢ BENCHMARK (VỚI 10 PROXIES):")
    logger.info(f"- Số trang đã quét: 5 (khoảng 100 bài báo)")
    logger.info(f"- Tổng thời gian hoàn thành: {total_time:.2f} giây")
    logger.info(f"- Tốc độ trung bình: {total_time / 100:.2f} giây/bài báo")
    logger.info("="*40)

if __name__ == "__main__":
    asyncio.run(benchmark_100_papers())
