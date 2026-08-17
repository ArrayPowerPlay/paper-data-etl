import os
from paper_etl.common.polite_session import PoliteSession
from paper_etl.discovery.oai_harvester import OAIHarvester
from paper_etl.enrichment.canonicalizer import Canonicalizer
from paper_etl.enrichment.html_enricher import HTMLEnricher
from paper_etl.enrichment.pdf_downloader import PDFDownloader
import json

def run_pipeline():
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Setup Session
    print("=== Setting up PoliteSession ===")
    session = PoliteSession(qps=0.1) # 1 request / 10 seconds to respect VJOL robots.txt 10s delay limit? Wait, 1 request / 10 sec is safe.
    
    # 2. Discovery (Phase 1)
    print("=== Running Phase 1: Discovery ===")
    harvester = OAIHarvester(session=session, output_dir=output_dir)
    # preflight is optional but good for setup
    harvester.preflight()
    
    # We just want 20 records for test.
    # The harvester fetches pages, so we might get 100 in the first page.
    # We pass max_records=20.
    raw_records, run_dir = harvester.harvest_records(max_records=20)
    
    if not raw_records:
        print("No records found.")
        return
        
    print(f"Harvested {len(raw_records)} raw XML records.")
    
    # Trim to exactly 20 if more were returned in the batch
    raw_records = raw_records[:20]
    
    # 3. Canonicalization & Enrichment (Phase 2)
    print("=== Running Phase 2: Canonicalization & Enrichment ===")
    run_id = os.path.basename(run_dir)
    
    canonicalizer = Canonicalizer(output_dir=output_dir)
    canonical_records = canonicalizer.process_records(raw_records, run_id)
    
    enricher = HTMLEnricher(session=session, output_dir=output_dir)
    enriched_records = enricher.enrich_records(canonical_records)
    
    downloader = PDFDownloader(session=session, output_dir=output_dir)
    final_records = downloader.download_pdfs(enriched_records)
    
    # Save final results
    result_path = os.path.join(output_dir, f"phase2_result_{run_id}.jsonl")
    with open(result_path, "w", encoding="utf-8") as f:
        for rec in final_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            
    print(f"Pipeline test completed successfully! Results saved to {result_path}")
    print(f"Summary:")
    downloaded = sum(1 for r in final_records if r.get("status") == "downloaded")
    print(f"  Total records: {len(final_records)}")
    print(f"  PDFs downloaded successfully: {downloaded}")

if __name__ == "__main__":
    run_pipeline()
