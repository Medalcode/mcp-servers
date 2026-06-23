import urllib.parse
import httpx
import logging
from bs4 import BeautifulSoup
import random

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]


async def scan_indeed(query: str, location: str = "Chile", filters: dict = None) -> list:
    import asyncio
    import json
    from services.browser_client import call_tool
    
    params = {"q": query, "l": location, "sort": "date"}
    url = f"https://cl.indeed.com/trabajo?{urllib.parse.urlencode(params)}"
    
    try:
        await call_tool("navigate", {"url": url})
        await asyncio.sleep(4)
        
        script = """
        const jobs = [];
        const cards = document.querySelectorAll('div.job_seen_beacon, div.jobsearch-SerpJobCard, div.cardOutline, li.css-1ac2h1w, div.slider_container li');
        for (const card of cards) {
            const titleEl = card.querySelector('h2 a, h2.jobTitle a, a.jobTitle, a[data-jk]');
            if (!titleEl) continue;
            const title = titleEl.innerText.trim();
            let url_rel = titleEl.getAttribute('href') || '';
            if (url_rel.startsWith('/')) url_rel = 'https://cl.indeed.com' + url_rel;
            
            const companyEl = card.querySelector('[data-testid="company-name"], span.companyName, .company a, .companyName');
            const company = companyEl ? companyEl.innerText.trim() : 'Confidencial';
            
            const locEl = card.querySelector('[data-testid="text-location"], div.companyLocation, .location');
            const loc = locEl ? locEl.innerText.trim() : '';
            
            const descEl = card.querySelector('[data-testid="job-snippet"], div.job-snippet, .summary, ul li');
            const desc = descEl ? descEl.innerText.trim() : '';
            
            const salaryEl = card.querySelector('[data-testid="attribute_snippet_testid"], .salary-snippet, .salary');
            const salary = salaryEl ? salaryEl.innerText.trim() : '';
            
            const dateEl = card.querySelector('[data-testid="job-date"], .date, .jobsearch-SerpJobCard-footer');
            const date = dateEl ? dateEl.innerText.trim() : '';
            
            jobs.push({ title, company, location: loc, url: url_rel, description: desc.substring(0, 500), salary, date, source: 'Indeed' });
        }
        return JSON.stringify(jobs);
        """
        
        res = await call_tool("run_script", {"script": script})
        
        # Parse the output from Browser MCP
        if "---" in res:
            json_str = res.split("---")[-1].strip()
        else:
            json_str = res.replace("[Engine: selenium]", "").strip()
            
        jobs = json.loads(json_str)
        return jobs
        
    except Exception as e:
        logger.warning("Indeed browser request failed: %s", e)
        return []
