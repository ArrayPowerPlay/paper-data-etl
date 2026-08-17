from lxml import etree as ET
import json
import os

class Canonicalizer:
    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        self.oai_namespace = {"oai": "http://www.openarchives.org/OAI/2.0/",
                              "dc": "http://purl.org/dc/elements/1.1/",
                              "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/"}

    def _ensure_dir(self, path):
        os.makedirs(path, exist_ok=True)

    def process_records(self, raw_records, run_id):
        print("Canonicalizing records...")
        jsonl_dir = os.path.join(self.output_dir, "canonical")
        self._ensure_dir(jsonl_dir)
        output_file = os.path.join(jsonl_dir, f"canonical_{run_id}.jsonl")
        
        canonical_records = []
        with open(output_file, "w", encoding="utf-8") as f:
            for xml_str in raw_records:
                try:
                    parser = ET.XMLParser(recover=True, encoding='utf-8')
                    record = ET.fromstring(xml_str.encode('utf-8') if isinstance(xml_str, str) else xml_str, parser=parser)
                    header = record.find(".//oai:header", self.oai_namespace)
                    metadata = record.find(".//oai:metadata", self.oai_namespace)
                    
                    if header is None or metadata is None:
                        continue
                        
                    oai_id = header.find("oai:identifier", self.oai_namespace).text
                    datestamp = header.find("oai:datestamp", self.oai_namespace).text
                    set_specs = [e.text for e in header.findall("oai:setSpec", self.oai_namespace)]
                    
                    dc = metadata.find("oai_dc:dc", self.oai_namespace)
                    titles = [e.text for e in dc.findall("dc:title", self.oai_namespace) if e.text]
                    creators = [e.text for e in dc.findall("dc:creator", self.oai_namespace) if e.text]
                    descriptions = [e.text for e in dc.findall("dc:description", self.oai_namespace) if e.text]
                    identifiers = [e.text for e in dc.findall("dc:identifier", self.oai_namespace) if e.text]
                    
                    article_url = None
                    doi = None
                    for ident in identifiers:
                        if ident.startswith("http") and "article/view" in ident:
                            article_url = ident
                        elif ident.startswith("http") and "doi.org" in ident:
                            doi = ident
                            
                    # Fix VJOL routing issue: URL might point to /index/ instead of the actual journal
                    if article_url and "/index/" in article_url and set_specs:
                        journal_acronym = set_specs[0].split(":")[0]
                        article_url = article_url.replace("/index/", f"/{journal_acronym}/")
                    
                    rec_dict = {
                        "oai_id": oai_id,
                        "datestamp": datestamp,
                        "set_specs": set_specs,
                        "titles": titles,
                        "authors": creators,
                        "abstracts": descriptions,
                        "article_url": article_url,
                        "doi": doi
                    }
                    
                    f.write(json.dumps(rec_dict, ensure_ascii=False) + "\n")
                    canonical_records.append(rec_dict)
                except Exception as e:
                    print(f"Error parsing record: {e}")
                    
        print(f"Canonicalized {len(canonical_records)} records.")
        return canonical_records
