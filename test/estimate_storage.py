import os
import glob
from lxml import etree

def estimate_storage():
    # Tìm file XML mới nhất đã tải
    runs = sorted(glob.glob("data/raw/oai/runs/*/page-000001.xml"))
    if not runs:
        print("Không tìm thấy file OAI-PMH nào. Chạy Phase 1 trước.")
        return
        
    latest_file = runs[-1]
    print(f"Đang đọc file: {latest_file}")
    
    # Parse XML lấy completeListSize
    parser = etree.XMLParser(recover=True)
    tree = etree.parse(latest_file, parser)
    ns = {'oai': 'http://www.openarchives.org/OAI/2.0/'}
    token = tree.find('.//oai:resumptionToken', ns)
    
    if token is not None and token.attrib.get('completeListSize'):
        total_papers = int(token.attrib.get('completeListSize'))
        print(f"Tổng số bài báo trên VJOL: {total_papers:,} bài")
        
        # Giả định trung bình 1.5MB mỗi file PDF
        avg_size_mb = 1.5 
        
        # Tính toán
        total_size_mb = total_papers * avg_size_mb
        total_size_gb = total_size_mb / 1024
        
        print("\n--- Ước tính lưu trữ (Chỉ tính PDF) ---")
        print(f"Kích thước trung bình/bài : {avg_size_mb} MB")
        print(f"Tổng dung lượng dự kiến   : {total_size_gb:.2f} GB")
        
        print("\n--- Ước tính nếu lưu JSON/Parquet (Text-only) ---")
        # Text thường khoảng 30KB - 50KB mỗi bài
        avg_text_kb = 40
        total_text_gb = (total_papers * avg_text_kb) / (1024 * 1024)
        print(f"Kích thước trung bình/bài : {avg_text_kb} KB")
        print(f"Tổng dung lượng dự kiến   : {total_text_gb:.2f} GB")
        
    else:
        print("Không thể tìm thấy resumptionToken / completeListSize trong file XML.")

if __name__ == "__main__":
    estimate_storage()
