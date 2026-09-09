import asyncio
import time
import os
import re
from curl_cffi import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
proxy_str = os.getenv("PROXIES", "")
proxy_list = [p.strip() for p in proxy_str.split(",")] if proxy_str else []

async def fetch_vjol_records(session):
    url = "https://vjol.info.vn/index.php/index/oai?verb=ListRecords&metadataPrefix=oai_dc"
    r = await session.get(url, timeout=30)
    
    # In ra một phần text nếu lỗi để debug
    if "<dc:identifier>" not in r.text:
        print(f"Lỗi fetch OAI-PMH: {r.text[:500]}")
        
    # Tìm tất cả thẻ <dc:identifier>
    links = re.findall(r'<dc:identifier>(http[^<]+)</dc:identifier>', r.text)
    
    # Lọc những link hợp lệ (chứa article/view)
    valid_links = [l for l in links if 'article/view' in l]
    
    # Lấy unique links
    unique_links = list(set(valid_links))
    return unique_links[:100]

async def download_worker(worker_id, session, queue, output_dir):
    while True:
        link = await queue.get()
        if link is None:
            queue.task_done()
            break
            
        try:
            # 1. Tải trang chi tiết (Abstract Page)
            r = await session.get(link, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # 2. Tìm link tải PDF
            pdf_link_tag = soup.find('a', class_=lambda c: c and 'pdf' in c.lower() and 'galley' in c.lower())
            if not pdf_link_tag:
                # Fallback tìm các thẻ a có href chứa article/view và có chữ pdf
                pdf_link_tag = soup.find('a', href=lambda h: h and '/article/view/' in h)
                
            if pdf_link_tag:
                # Chuyển view thành download để tải trực tiếp file PDF
                pdf_url = pdf_link_tag['href'].replace('/view/', '/download/')
                
                # 3. Tải PDF
                r_pdf = await session.get(pdf_url, timeout=30)
                if r_pdf.content.startswith(b'%PDF'):
                    filename = os.path.join(output_dir, link.split('/')[-1] + ".pdf")
                    with open(filename, 'wb') as f:
                        f.write(r_pdf.content)
                else:
                    print(f"[Worker {worker_id}] File tải về không phải PDF: {link}")
        except Exception as e:
            pass # Bỏ qua lỗi in ra màn hình để tránh trôi log
            
        queue.task_done()

async def benchmark_vjol():
    output_dir = "data/vjol_temp"
    os.makedirs(output_dir, exist_ok=True)
    
    # Xóa file cũ
    for f in os.listdir(output_dir):
        os.remove(os.path.join(output_dir, f))
        
    sessions = []
    for p in proxy_list:
        proxy_dict = {"http": p, "https": p} if p else None
        sessions.append(requests.AsyncSession(impersonate="chrome110", proxies=proxy_dict))
        
    if not sessions:
        sessions.append(requests.AsyncSession(impersonate="chrome110"))

    print("Đang lấy danh sách metadata từ OAI-PMH của VJOL...")
    links = await fetch_vjol_records(sessions[0])
    print(f"-> Đã lấy được {len(links)} links hợp lệ.")
    print("Bắt đầu tải PDF song song với 10 Proxies...")
    
    queue = asyncio.Queue()
    for link in links:
        await queue.put(link)
        
    for _ in sessions:
        await queue.put(None)
        
    start_time = time.time()
    
    tasks = []
    for i, session in enumerate(sessions):
        tasks.append(asyncio.create_task(download_worker(i, session, queue, output_dir)))
        
    await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    downloaded = len([f for f in os.listdir(output_dir) if f.endswith(".pdf")])
    
    print("\n" + "="*40)
    print("KẾT QUẢ TẢI VJOL (VỚI 10 PROXIES):")
    print(f"- Số lượng tải thành công: {downloaded} / {len(links)} bài")
    print(f"- Tổng thời gian: {total_time:.2f} giây")
    if downloaded > 0:
        print(f"- Tốc độ trung bình: {total_time / downloaded:.2f} giây/bài")
    print("="*40)
    
    for s in sessions:
        await s.close()

if __name__ == "__main__":
    asyncio.run(benchmark_vjol())
