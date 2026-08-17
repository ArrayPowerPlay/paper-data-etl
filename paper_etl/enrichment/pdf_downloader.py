import os
import hashlib
import time
from bs4 import BeautifulSoup

class PDFDownloader:
    def __init__(self, session, output_dir="data"):
        self.session = session
        self.output_dir = output_dir

    def _ensure_dir(self, path):
        os.makedirs(path, exist_ok=True)

    def download_pdfs(self, records):
        print("Downloading PDFs...")
        pdf_dir = os.path.join(self.output_dir, "raw", "pdf")
        self._ensure_dir(pdf_dir)
        
        downloaded_records = []
        for rec in records:
            pdf_url = rec.get("pdf_url")
            galley_url = rec.get("galley_url")
            
            if not pdf_url and not galley_url:
                rec["status"] = "missing_pdf_url"
                downloaded_records.append(rec)
                continue
                
            safe_id = rec["oai_id"].replace(":", "_").replace("/", "_")
            # We don't have SHA256 yet before downloading, so we'll save it by OAI ID first
            # and rename it after computing hash.
            temp_path = os.path.join(pdf_dir, f"{safe_id}_temp.pdf")
            
            try:
                # If we only have galley_url, we need to fetch the viewer page to find the real PDF link
                if not pdf_url and galley_url:
                    print(f"Fetching Galley Viewer: {galley_url}")
                    g_resp = self.session.get(galley_url)
                    g_resp.raise_for_status()
                    soup = BeautifulSoup(g_resp.text, "html.parser")
                    dl_link = soup.find("a", class_="download")
                    if dl_link and "href" in dl_link.attrs:
                        pdf_url = dl_link["href"]
                    else:
                        # Fallback: Sometimes just replacing 'view' with 'download' works for 2-part ID
                        pdf_url = galley_url.replace("/view/", "/download/")
                
                print(f"Downloading PDF: {pdf_url}")
                # Use stream=True to handle large files
                response = self.session.get(pdf_url, stream=True)
                response.raise_for_status()
                
                hasher = hashlib.sha256()
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        hasher.update(chunk)
                
                # Check magic bytes
                with open(temp_path, "rb") as f:
                    magic = f.read(4)
                
                if magic != b"%PDF":
                    print(f"File at {pdf_url} is not a valid PDF (Magic bytes: {magic})")
                    os.remove(temp_path)
                    rec["status"] = "corrupt_pdf"
                    downloaded_records.append(rec)
                    continue
                    
                file_hash = hasher.hexdigest()
                final_path = os.path.join(pdf_dir, f"{file_hash}.pdf")
                
                if os.path.exists(final_path):
                    print(f"PDF already exists: {file_hash}")
                    os.remove(temp_path)
                else:
                    os.rename(temp_path, final_path)
                    
                rec["pdf_hash"] = file_hash
                rec["pdf_path"] = final_path
                rec["status"] = "downloaded"
            except Exception as e:
                print(f"Error downloading {pdf_url}: {e}")
                rec["status"] = "download_error"
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
            downloaded_records.append(rec)
            
        print(f"Completed processing {len(records)} PDFs.")
        return downloaded_records
