import os
import json
from bs4 import BeautifulSoup
import time

class HTMLEnricher:
    def __init__(self, session, output_dir="data"):
        self.session = session
        self.output_dir = output_dir

    def _ensure_dir(self, path):
        os.makedirs(path, exist_ok=True)

    def enrich_records(self, records):
        print("Enriching records with HTML metadata...")
        enriched_dir = os.path.join(self.output_dir, "enriched")
        html_dir = os.path.join(self.output_dir, "raw", "html")
        self._ensure_dir(enriched_dir)
        self._ensure_dir(html_dir)
        
        enriched_records = []
        for rec in records:
            article_url = rec.get("article_url")
            if not article_url:
                enriched_records.append(rec)
                continue
                
            try:
                print(f"Fetching HTML: {article_url}")
                response = self.session.get(article_url)
                if response.status_code == 200:
                    html_content = response.text
                    
                    # Save raw HTML
                    safe_id = rec["oai_id"].replace(":", "_").replace("/", "_")
                    html_path = os.path.join(html_dir, f"{safe_id}.html")
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(html_content)
                        
                    soup = BeautifulSoup(html_content, "html.parser")
                    pdf_url_tag = soup.find("meta", attrs={"name": "citation_pdf_url"})
                    if pdf_url_tag:
                        rec["pdf_url"] = pdf_url_tag.get("content")
                    else:
                        # Fallback for OJS 3: Find galley link
                        galley_link = soup.find("a", class_="obj_galley_link")
                        if galley_link and "href" in galley_link.attrs:
                            rec["galley_url"] = galley_link["href"]
                            
                    # Can extract more citation_* tags if needed
            except Exception as e:
                print(f"Error enriching {article_url}: {e}")
                
            enriched_records.append(rec)
            
        return enriched_records
