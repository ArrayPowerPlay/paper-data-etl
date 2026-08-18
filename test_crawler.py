import asyncio
import os
import sys

# Ensure src is in pythonpath
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.discovery.vista_crawler import VistaCrawler
from src.common.logger import setup_logger

logger = setup_logger(__name__)

async def test_5_papers():
    # Sử dụng output_dir là "data" (thực tế)
    crawler = VistaCrawler(output_dir="data", max_concurrent_requests=1)
    
    original_extract = crawler.extract_links_from_page
    
    async def mock_extract(session, offset):
        # Override to only fetch exactly 5 articles
        articles = await original_extract(session, offset)
        return articles[:5]
        
    crawler.extract_links_from_page = mock_extract
    
    # Chỉ quét trang đầu tiên (start_page=0, end_page=1)
    await crawler.run_overclocked_pipeline(start_page=0, end_page=1)

if __name__ == "__main__":
    logger.info("Bắt đầu tải thử nghiệm 5 papers...")
    asyncio.run(test_5_papers())
