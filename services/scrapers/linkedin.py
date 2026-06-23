import logging
import json
from services.browser_client import call_tool, ensure_browser
from servers.linkedin import _ensure_linkedin_session

logger = logging.getLogger(__name__)

async def scan_linkedin(query: str, location: str = "Chile", filters: dict = None) -> list:
    """
    Generic scraper for LinkedIn Jobs.
    """
    jobs = []
    
    try:
        await ensure_browser()
        await _ensure_linkedin_session()
        
        search_keywords = query.strip()
        params = f"keywords={search_keywords.replace(' ', '%20')}&location={location.replace(' ', '%20')}"
        
        if filters:
            if filters.get('modality') == 'remote':
                params += "&f_WT=2"
            if filters.get('date') == 'today':
                params += "&f_TPR=r86400"
            elif filters.get('date') == 'week':
                params += "&f_TPR=r604800"
            elif filters.get('date') == 'month':
                params += "&f_TPR=r2592000"
        
        url = f"https://www.linkedin.com/jobs/search/?{params}"
        await call_tool("navigate", {"url": url})
        await call_tool("wait", {"ms": 3000})

        script = f"""
            async function scrollAndExtract() {{
                const container = document.querySelector('.jobs-search-results-list') || window;
                let previousHeight = 0;
                let sameHeightCount = 0;
                
                // Scroll down a few times to load more jobs
                for (let i = 0; i < 10; i++) {{
                    if (container === window) {{
                        window.scrollTo(0, document.body.scrollHeight);
                    }} else {{
                        container.scrollTo(0, container.scrollHeight);
                    }}
                    await new Promise(r => setTimeout(r, 800));
                    
                    let currentHeight = container === window ? document.body.scrollHeight : container.scrollHeight;
                    if (currentHeight === previousHeight) {{
                        sameHeightCount++;
                        if (sameHeightCount > 2) break; // Reached bottom
                    }} else {{
                        sameHeightCount = 0;
                    }}
                    previousHeight = currentHeight;
                }}

                const items = document.querySelectorAll('.job-card-container, .jobs-search-results__list li, [data-job-id], article.jobs-search-results__list-item');
                const jobs = [];
                for(const item of items) {{
                    const titleEl = item.querySelector('.job-card-list__title, .job-card-container__link, .job-card-search__title, a[data-anonymize="job-title"]');
                    const companyEl = item.querySelector('.job-card-container__company-name, .job-card-search__company-name, [data-anonymize="company-name"]');
                    const locEl = item.querySelector('.job-card-container__metadata-item, .job-card-search__location, [data-anonymize="location"]');
                    const link = titleEl?.closest('a') || titleEl?.querySelector('a') || item.querySelector('a[href*="/jobs/view/"]');
                    if(titleEl) {{
                        const href = link ? (link.href || link.getAttribute('href')) : '';
                        jobs.push({{
                            title: (titleEl.textContent || '').trim(),
                            company: (companyEl?.textContent || '').trim(),
                            location: (locEl?.textContent || '').trim(),
                            url: href,
                            description: "",
                            source: "LinkedIn"
                        }});
                    }}
                }}
                return JSON.stringify(jobs);
            }}
            return await scrollAndExtract();
        """
        
        res2 = await call_tool("run_script", {"script": script})
        data = json.loads(res2.split("---")[-1].strip()) if "---" in res2 else json.loads(res2.replace("[Engine: selenium]", "").strip())
        
        for j in data:
            if j.get("title"):
                jobs.append(j)
                
    except RuntimeError as e:
        if "checkpoint" in str(e).lower() or "credentials" in str(e).lower():
            logger.error(f"LinkedIn Auth Error: {e}")
            jobs.append({
                "title": f"⚠️ REQUIERE LOGIN: LinkedIn",
                "company": "LinkedIn",
                "location": location,
                "url": "https://www.linkedin.com/login",
                "description": f"Debes ejecutar 'python run_debug_login.py' para verificar LinkedIn. Detalle: {e}",
                "source": "System"
            })
        else:
            logger.warning(f"Error scraping LinkedIn: {e}")
            
    except Exception as e:
        logger.warning(f"Unexpected error scraping LinkedIn: {e}")
        
    return jobs
