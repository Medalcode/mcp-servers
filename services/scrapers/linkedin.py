import logging
import json
import asyncio
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
        try:
            await _ensure_linkedin_session()
        except RuntimeError as e:
            logger.warning(f"LinkedIn auth missing, proceeding unauthenticated: {e}")
        
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

        # Scroll down a few times to load more jobs (managed in Python to avoid JS blocklist)
        previous_height = 0
        same_height_count = 0
        for _ in range(25):
            scroll_script = "window.scrollTo(0, document.body.scrollHeight); const c = document.querySelector('.jobs-search-results-list'); if (c) c.scrollTo(0, c.scrollHeight); return document.body.scrollHeight;"
            current_height = await call_tool("run_script", {"script": scroll_script})
            await asyncio.sleep(1)
            
            # Simple check if we reached bottom
            try:
                curr_h = int(str(current_height).replace("[Engine: selenium]", "").strip())
                if curr_h == previous_height:
                    same_height_count += 1
                    if same_height_count > 2:
                        break
                else:
                    same_height_count = 0
                previous_height = curr_h
            except Exception:
                pass

        script = """
            const items = document.querySelectorAll('.job-card-container, .base-search-card, [data-job-id], article.jobs-search-results__list-item');
            const jobs = [];
            for(const item of items) {
                const titleEl = item.querySelector('.job-card-list__title, .job-card-container__link, .job-card-search__title, a[data-anonymize="job-title"], .base-search-card__title, .sr-only');
                const companyEl = item.querySelector('.job-card-container__company-name, .job-card-search__company-name, [data-anonymize="company-name"], .base-search-card__subtitle');
                const locEl = item.querySelector('.job-card-container__metadata-item, .job-card-search__location, [data-anonymize="location"], .job-search-card__location');
                const link = titleEl?.closest('a') || titleEl?.querySelector('a') || item.querySelector('a[href*="/jobs/view/"], a.base-card__full-link') || item.closest('a');
                
                let title = (titleEl ? titleEl.textContent : '').trim();
                if (!title && item.querySelector('.sr-only')) {
                    title = item.querySelector('.sr-only').textContent.trim();
                }
                
                if(title) {
                    const href = link ? (link.href || link.getAttribute('href')) : '';
                    jobs.push({
                        title: title,
                        company: (companyEl?.textContent || '').trim(),
                        location: (locEl?.textContent || '').trim(),
                        url: href,
                        description: "",
                        source: "LinkedIn"
                    });
                }
            }
            return JSON.stringify(jobs);
        """
        
        import os
        old_max = os.environ.get("BROWSER_TEXT_MAX")
        os.environ["BROWSER_TEXT_MAX"] = "500000"
        try:
            res2 = await call_tool("run_script", {"script": script})
            raw_json = res2.split("---")[-1].strip() if "---" in res2 else res2.replace("[Engine: selenium]", "").strip()
            data = json.loads(raw_json) if raw_json else []
        finally:
            if old_max is not None:
                os.environ["BROWSER_TEXT_MAX"] = old_max
            else:
                del os.environ["BROWSER_TEXT_MAX"]
        
        for j in data:
            if j.get("title"):
                jobs.append(j)
                
    except RuntimeError as e:
        if "checkpoint" in str(e).lower() or "credentials" in str(e).lower():
            logger.error(f"LinkedIn Auth Error: {e}")
            jobs.append({
                "title": "⚠️ REQUIERE LOGIN: LinkedIn",
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
