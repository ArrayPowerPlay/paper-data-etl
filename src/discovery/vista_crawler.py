import os
import asyncio
import hashlib
import json
import logging
from bs4 import BeautifulSoup
from curl_cffi import requests
from urllib.parse import urljoin
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

class VistaCrawler:
    def __init__(self, output_dir="data", max_concurrent_requests=2):
        self.base_url = "https://sti.vista.gov.vn"
        self.output_dir = output_dir
        self.raw_pdf_dir = os.path.join(output_dir, "raw", "pdf")
        self.queue_file = os.path.join(output_dir, "discovery_queue.jsonl")
        self.downloaded_log = os.path.join(output_dir, "downloaded_log.jsonl")
        self.max_concurrent = max_concurrent_requests
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self.processed_ids = set()
        
        os.makedirs(self.raw_pdf_dir, exist_ok=True)
        self._load_processed_ids()
        
    def _load_processed_ids(self):
        """Khôi phục trạng thái từ lần chạy trước để không tải lại file đã tải."""
        if os.path.exists(self.downloaded_log):
            with open(self.downloaded_log, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        if record.get("status") == "downloaded":
                            self.processed_ids.add(record.get("oai_id"))
                    except:
                        pass
        logger.info(f"Đã khôi phục {len(self.processed_ids)} bài báo đã tải thành công từ lần chạy trước.")
        
    async def _fetch_page(self, session, url, max_retries=3):
        """Fetch a page asynchronously using TLS spoofing with Retry + Backoff."""
        for attempt in range(max_retries):
            async with self.semaphore:
                try:
                    # Impersonate Chrome to bypass WAF
                    response = await session.get(url, impersonate="chrome110", timeout=15)
                    response.raise_for_status()
                    return response.text, response.content
                except Exception as e:
                    # Nếu là lỗi 429 (Too Many Requests), nghỉ ngơi lâu hơn một chút
                    is_429 = "429" in str(e)
                    wait_time = (2 ** attempt) + (5 if is_429 else 0)
                    
                    if attempt < max_retries - 1:
                        logger.warning(f"Lỗi tải {url}: {e}. Đang thử lại (Lần {attempt + 1}/{max_retries}) sau {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Thất bại hoàn toàn sau {max_retries} lần tải {url}: {e}")
                        return None, None

    async def extract_links_from_page(self, session, offset):
        """Fetch a listing page and extract article metadata and PDF links."""
        url = f"{self.base_url}/?mod=publication&page={offset}"
        logger.info(f"Scraping page {offset//20 + 1}...")
        
        html_text, _ = await self._fetch_page(session, url)
        if not html_text:
            return []
            
        soup = BeautifulSoup(html_text, "html.parser")
        articles = []
        
        # NOTE: CSS selectors here are generic. Needs tuning based on actual VISTA DOM.
        # But based on typical VISTA structure, publications are usually in a list or table.
        # We look for all 'a' tags that contain '/publication/download/'
        download_links = soup.find_all("a", href=lambda href: href and "/publication/download/" in href)
        
        for link in download_links:
            pdf_url = urljoin(self.base_url, link["href"])
            # Try to find the title by looking at the parent container
            container = link.find_parent("div", class_="item") or link.find_parent("tr")
            title = ""
            if container:
                title_tag = container.find("a", href=lambda href: href and "/publication/view/" in href)
                if title_tag:
                    title = title_tag.get_text(strip=True)
            
            # Extract ID from URL
            file_id = pdf_url.split("/")[-1].replace(".html", "")
            
            # Deduplication Check
            if file_id in self.processed_ids:
                continue
                
            articles.append({
                "oai_id": file_id,
                "title": title,
                "pdf_url": pdf_url,
                "scraped_at": datetime.now().isoformat()
            })
            
        return articles

    async def download_pdf(self, session, record):
        """Download the PDF using the exact same session (sharing cookies)."""
        pdf_url = record["pdf_url"]
        temp_path = os.path.join(self.raw_pdf_dir, f"{record['oai_id']}_temp.pdf")
        
        # Check if we already have it
        # Since we use SHA256 for final path, we might not know it until we download.
        # But we can check if a file with this oai_id exists if we saved mapping. 
        # For simplicity, we download to temp and hash it.
        
        logger.info(f"Downloading PDF: {pdf_url}")
        _, content = await self._fetch_page(session, pdf_url)
        if not content:
            record["status"] = "download_failed"
            return record
            
        # Check magic bytes to avoid WAF HTML pages disguised as PDFs
        if not content.startswith(b"%PDF"):
            logger.warning(f"File {pdf_url} is not a PDF! Probably blocked by WAF.")
            record["status"] = "corrupt_pdf"
            return record
            
        # Hash and save
        file_hash = hashlib.sha256(content).hexdigest()
        final_path = os.path.join(self.raw_pdf_dir, f"{file_hash}.pdf")
        
        if not os.path.exists(final_path):
            with open(final_path, "wb") as f:
                f.write(content)
        
        record["pdf_hash"] = file_hash
        record["pdf_path"] = final_path
        record["status"] = "downloaded"
        return record

    async def _producer(self, session, queue, start_page, end_page):
        """Producer: Scrape pagination and put PDF records into the Queue."""
        page_idx = start_page
        while True:
            if end_page is not None and page_idx >= end_page:
                logger.info(f"Đã đạt giới hạn end_page={end_page}. Dừng quét.")
                break
                
            offset = page_idx * 20
            articles = await self.extract_links_from_page(session, offset)
            
            # Điều kiện dừng tự động: Nếu trang trả về không có bài báo nào (Cạn kiệt)
            if not articles:
                logger.info(f"Không tìm thấy bài báo nào ở trang {page_idx}. Đã quét đến cuối danh sách. Dừng quét.")
                break
            
            # Save metadata to queue file immediately
            with open(self.queue_file, "a", encoding="utf-8") as f:
                for art in articles:
                    f.write(json.dumps(art, ensure_ascii=False) + "\n")
                    await queue.put(art)
                    
            # A small breather to not overload the server entirely
            await asyncio.sleep(1)
            page_idx += 1
            
        # Signal workers to stop
        for _ in range(self.max_concurrent):
            await queue.put(None)

    async def _consumer(self, session, queue):
        """Consumer: Download PDFs from the Queue."""
        while True:
            record = await queue.get()
            if record is None:
                queue.task_done()
                break
                
            updated_record = await self.download_pdf(session, record)
            
            # Ghi nhận kết quả tải vào file log gốc
            with open(self.downloaded_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(updated_record, ensure_ascii=False) + "\n")
                
            queue.task_done()

    async def run_overclocked_pipeline(self, start_page=0, end_page=None):
        """Run the Discovery and Download pipeline concurrently."""
        queue = asyncio.Queue(maxsize=100)
        
        # AsyncSession with curl_cffi handles TLS spoofing and connection pooling
        async with requests.AsyncSession(impersonate="chrome110") as session:
            # Create Producer task
            producer_task = asyncio.create_task(
                self._producer(session, queue, start_page, end_page)
            )
            
            # Create Consumer tasks (Workers)
            consumers = []
            # Use max_concurrent workers for downloading
            for _ in range(self.max_concurrent):
                task = asyncio.create_task(self._consumer(session, queue))
                consumers.append(task)
                
            await asyncio.gather(producer_task, *consumers)
            logger.info("Pipeline completed for the specified page range.")

if __name__ == "__main__":
    from src.common.logger import setup_logger
    setup_logger(__name__)
    
    crawler = VistaCrawler()
    # Test run for first 5 pages (100 articles)
    asyncio.run(crawler.run_overclocked_pipeline(start_page=0, end_page=5))
