import sqlite3
import requests
from bs4 import BeautifulSoup

c = sqlite3.connect('data/history.db').cursor()
c.execute('SELECT name, ph_url, official_url FROM products WHERE name LIKE "%Singularity%"')
row = c.fetchone()
print('DB Row:', row)

if row:
    ph_url = row[1]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    r = requests.get(ph_url, headers=headers, timeout=10)
    print('PH Page Status:', r.status_code)
    soup = BeautifulSoup(r.text, 'html.parser')
    for a in soup.find_all('a'):
        href = a.get('href', '')
        text = a.text.strip()
        if 'visit' in text.lower() or 'get it' in text.lower() or 'website' in text.lower():
            print('Candidate button:', text, 'href=', href)
