import os
import asyncio
import argparse
from src.discovery.vista_crawler import VistaCrawler
from src.common.logger import setup_logger

logger = setup_logger(__name__)

def run_pipeline(start_page, end_page):
    logger.info(f"Starting VISTA Crawler pipeline from page {start_page} to {end_page}")
    crawler = VistaCrawler()
    asyncio.run(crawler.run_overclocked_pipeline(start_page=start_page, end_page=end_page))
    logger.info("Pipeline Execution Completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VISTA Paper ETL")
    parser.add_argument("--start-page", type=int, default=0, help="Starting page index")
    parser.add_argument("--end-page", type=int, default=1, help="Ending page index")
    args = parser.parse_args()
    
    run_pipeline(args.start_page, args.end_page)
