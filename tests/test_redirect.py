import requests

url = "https://www.producthunt.com/r/p/1266692?app_id=339"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
}

s = requests.Session()
r = s.get(url, headers=headers, allow_redirects=True, timeout=10)
print("Status:", r.status_code)
print("Final URL:", r.url)
