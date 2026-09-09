import requests
import time
from bs4 import BeautifulSoup

def test_login_and_rate_limit():
    session = requests.Session()
    
    # URL login của VJOL OJS
    login_url = "https://www.vjol.info.vn/index.php/index/login/signIn"
    
    print("Truy cập trang đăng nhập...")
    response = session.get("https://www.vjol.info.vn/index.php/index/login", timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    csrf_token = ""
    csrf_input = soup.find('input', {'name': 'csrfToken'})
    if csrf_input:
        csrf_token = csrf_input.get('value', '')
        
    source = ""
    source_input = soup.find('input', {'name': 'source'})
    if source_input:
        source = source_input.get('value', '')
            
    # Nghỉ 5 giây trước khi post để tránh 429 do rate limit chung
    print("Đợi 5s để tránh rate limit lúc lấy form...")
    time.sleep(5.0)

    # Payload đăng nhập
    payload = {
        'csrfToken': csrf_token,
        'source': source,
        'username': '1dinh1',
        'password': 'AncientOnex@1',
        'remember': '1'
    }
    
    print("Thực hiện POST đăng nhập...")
    login_response = session.post(login_url, data=payload, allow_redirects=False)
    
    print(f"Login Response Status: {login_response.status_code}")
    print(f"Cookies sau đăng nhập: {session.cookies.get_dict()}")
    
    if 'OJS_V4_SSID' in session.cookies or login_response.status_code in [302, 303]:
        print("=> Đăng nhập thành công!")
    else:
        print("=> Đăng nhập thất bại (có thể do sai thông tin hoặc bị chặn).")
        
    print("Đợi 5s trước khi test xả liên tục...")
    time.sleep(5.0)

    print("\nBắt đầu test rate limit (gửi 5 request liên tục không delay)...")
    for i in range(5):
        test_url = "https://www.vjol.info.vn/index.php/index/oai?verb=Identify"
        res = session.get(test_url, timeout=10)
        print(f"Request {i+1}: Status {res.status_code}")
        if res.status_code == 429:
            print("=> Bị lỗi 429 Too Many Requests! Đăng nhập KHÔNG giúp nới lỏng rate limit.")
            return

if __name__ == "__main__":
    test_login_and_rate_limit()
