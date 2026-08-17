import os
import time
import json
import xml.etree.ElementTree as StdET
from lxml import etree as ET
from datetime import datetime
from urllib.parse import urlencode

class OAIHarvester:
    def __init__(self, session, base_url="https://www.vjol.info.vn/index.php/index/oai", output_dir="data"):
        self.session = session
        self.base_url = base_url
        self.output_dir = output_dir
        self.oai_namespace = {"oai": "http://www.openarchives.org/OAI/2.0/"}

    def _ensure_dir(self, path):
        os.makedirs(path, exist_ok=True)

    def _fetch_xml(self, params):
        url = f"{self.base_url}?{urlencode(params)}"
        print(f"Fetching: {url}")
        response = self.session.get(url)
        response.raise_for_status()
        return response.content

    def preflight(self):
        """Phase 1: Preflight checks."""
        print("Running preflight checks...")
        preflight_dir = os.path.join(self.output_dir, "raw", "oai")
        self._ensure_dir(preflight_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for verb in ["Identify", "ListMetadataFormats", "ListSets"]:
            try:
                content = self._fetch_xml({"verb": verb})
                with open(os.path.join(preflight_dir, f"{verb.lower()}-{timestamp}.xml"), "wb") as f:
                    f.write(content)
            except Exception as e:
                print(f"Failed to fetch {verb}: {e}")
        print("Preflight completed.")

    def harvest_records(self, metadata_prefix="oai_dc", max_records=None):
        """Phase 1: Harvest records with resumption token."""
        print("Harvesting OAI records...")
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(self.output_dir, "raw", "oai", "runs", run_id)
        self._ensure_dir(run_dir)

        params = {"verb": "ListRecords", "metadataPrefix": metadata_prefix}
        page = 1
        total_harvested = 0
        records_collected = []

        while True:
            content = self._fetch_xml(params)
            file_path = os.path.join(run_dir, f"page-{page:06d}.xml")
            with open(file_path, "wb") as f:
                f.write(content)

            parser = ET.XMLParser(recover=True, encoding='utf-8')
            root = ET.fromstring(content, parser=parser)
            records = root.findall(".//oai:record", self.oai_namespace)
            records_collected.extend([ET.tostring(r, encoding="unicode") for r in records])
            total_harvested += len(records)
            print(f"Page {page} harvested {len(records)} records. Total: {total_harvested}")

            if max_records and total_harvested >= max_records:
                print(f"Reached max_records ({max_records}). Stopping harvest.")
                break

            resumption_token = root.find(".//oai:resumptionToken", self.oai_namespace)
            if resumption_token is not None and resumption_token.text:
                params = {"verb": "ListRecords", "resumptionToken": resumption_token.text}
                page += 1
            else:
                break
        
        return records_collected, run_dir
