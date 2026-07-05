import urllib.parse
import logging

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]


async def scan_trabajando(query: str, location: str = "Chile", filters: dict = None) -> list:
    import asyncio
    import json
    from services.browser_client import call_tool
    
    params = {"q": query, "l": location}
    url = f"https://www.trabajando.cl/trabajo-empleo/?{urllib.parse.urlencode(params)}"
    
    try:
        await call_tool("navigate", {"url": url})
        await asyncio.sleep(4)
        
        script = """
        const jobs = [];
        const cards = document.querySelectorAll('article.oferta, div.oferta, div[class*=oferta], div.job-item, tr.oferta');
        for (const card of cards) {
            const titleEl = card.querySelector('h2 a, h3 a, a[href*="/oferta/"]');
            if (!titleEl) continue;
            const title = titleEl.innerText.trim();
            let url_rel = titleEl.getAttribute('href') || '';
            const job_url = url_rel.startsWith('http') ? url_rel : `https://www.trabajando.cl${url_rel}`;
            
            const companyEl = card.querySelector('.empresa, .company, [class*=empresa]');
            const company = companyEl ? companyEl.innerText.trim() : 'Confidencial';
            
            const locEl = card.querySelector('.ubicacion, .location, [class*=ubicacion]');
            const loc = locEl ? locEl.innerText.trim() : '';
            
            const descEl = card.querySelector('.descripcion, .description, .resumen, p');
            const desc = descEl ? descEl.innerText.trim() : '';
            
            jobs.push({ title, company, location: loc, url: job_url, description: desc.substring(0, 500), source: 'Trabajando.cl' });
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
        logger.warning("Trabajando browser request failed: %s", e)
        return []
