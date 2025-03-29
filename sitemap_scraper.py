import requests
import json
import concurrent.futures
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from datetime import datetime
import threading

# تنظیمات عمومی
MAIN_SITEMAP_URL = "https://bslthemes.com/sitemap_index.xml"
OUTPUT_FILE = "sitemap_results.json"
MAX_WORKERS = 5  # تعداد پردازه‌های موازی
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

# ساختار داده‌های گلوبال با قفل برای پردازش ایمن
sitemap_data = []
lock = threading.Lock()

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def process_sitemap(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        if 'sitemapindex' in response.text.lower():
            with lock:
                sitemap_data.append({"type": "sitemapindex", "url": url})
            process_sitemap_index(response.text)
            
        elif 'urlset' in response.text.lower():
            urls = process_urlset(response.text)
            with lock:
                sitemap_data.extend(urls)
                
    except Exception as e:
        print(f"Error processing {url}: {str(e)}")

def process_sitemap_index(xml_content):
    root = ET.fromstring(xml_content)
    sitemap_urls = [elem.text for elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(process_sitemap, filter(is_valid_url, sitemap_urls))

def process_urlset(xml_content):
    root = ET.fromstring(xml_content)
    urls = []
    
    for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
        entry = {
            "url": url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc').text,
            "lastmod": url.findtext('{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod', ''),
            "priority": url.findtext('{http://www.sitemaps.org/schemas/sitemap/0.9}priority', ''),
            "changefreq": url.findtext('{http://www.sitemaps.org/schemas/sitemap/0.9}changefreq', '')
        }
        if is_valid_url(entry["url"]):
            urls.append(entry)
    
    return urls

def save_results():
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            "metadata": {
                "website": "https://bslthemes.com",
                "generated_at": datetime.now().isoformat(),
                "total_urls": len([x for x in sitemap_data if x.get("type") != "sitemapindex"])
            },
            "sitemaps": [x for x in sitemap_data if x.get("type") == "sitemapindex"],
            "urls": [x for x in sitemap_data if x.get("type") is None]
        }, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    start_time = datetime.now()
    print(f"[{start_time}] Starting sitemap processing...")
    
    process_sitemap(MAIN_SITEMAP_URL)
    save_results()
    
    end_time = datetime.now()
    print(f"[{end_time}] Processing completed in {end_time - start_time}")
    print(f"Results saved to {OUTPUT_FILE}")