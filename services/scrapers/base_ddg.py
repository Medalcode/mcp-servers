import httpx
import urllib.parse
from bs4 import BeautifulSoup
import logging
import random
import re

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0"
]

async def scan_duckduckgo(domain: str, source_name: str, query: str, location: str = "Chile", filters: dict = None) -> list:
    """
    Generic scraper that relies on DuckDuckGo HTML search to bypass ATS WAFs.
    Useful for Eightfold, SuccessFactors, Workday, etc.
    """
    ddg_query = f"site:{domain} \"{query}\" {location}"
    
    # Process basic filters for search terms
    if filters:
        if filters.get('modality') == 'remote':
            ddg_query += " (remote OR remoto)"
        if filters.get('date') in ['today', 'week', 'month']:
            # DDG doesn't perfectly support date filters in HTML POST easily without df param
            # We will use df param: d=past day, w=past week, m=past month
            pass
            
    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://html.duckduckgo.com",
    }
    
    data = {"q": ddg_query}
    
    # Date filters in DDG HTML (only works occasionally via POST, but worth a try)
    if filters and filters.get('date'):
        d = filters.get('date')
        if d == 'today':
            data["df"] = "d"
        elif d == 'week':
            data["df"] = "w"
        elif d == 'month':
            data["df"] = "m"

    jobs = []
    
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.post(url, data=data, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"DDG HTML returned {resp.status_code} for {domain}")
                return []
                
            soup = BeautifulSoup(resp.text, 'lxml')
            results = soup.select(".result__body")
            
            for r in results:
                title_el = r.select_one(".result__title")
                if not title_el:
                    continue
                    
                title = title_el.get_text(strip=True)
                
                # Clean up title if it contains the company name
                clean_title = re.sub(r'[-\|].*$', '', title).strip()
                
                # Extract URL
                snippet_el = r.select_one(".result__snippet")
                url_el = r.select_one(".result__url")
                
                raw_url = snippet_el['href'] if snippet_el else url_el.get('href', "") if url_el else ""
                
                # Unpack DDG redirect URL
                if "uddg=" in raw_url:
                    try:
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query)
                        raw_url = parsed.get('uddg', [raw_url])[0]
                    except Exception:
                        pass
                
                if not raw_url.startswith("http"):
                    raw_url = "https://" + raw_url
                    
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                
                jobs.append({
                    "title": clean_title,
                    "company": source_name,
                    "location": location, # We assume the location based on the search query
                    "url": raw_url,
                    "description": snippet[:500],
                    "source": source_name,
                })
                
    except Exception as e:
        logger.warning(f"Error scraping DDG for {domain}: {e}")
        
    return jobs
