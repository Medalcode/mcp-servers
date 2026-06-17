import asyncio
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from services.job_service import search_jobs
from tools.auto_apply_tools import _batch_apply_one

async def main():
    print("Searching jobs on trabajando.cl...")
    # Fetch some jobs specifically using the Trabajando scraper or general search
    # Instead of full search, let's just search for python jobs.
    jobs = await search_jobs(query="Python", location="Chile")
    
    # Filter for trabajando.cl
    tb_jobs = [j for j in jobs if "trabajando" in j.get("url", "")]
    
    if not tb_jobs:
        print("No jobs found on trabajando.cl to test.")
        return
        
    test_job = tb_jobs[0]
    print(f"\nFound job: {test_job.get('title')} - {test_job.get('url')}")
    print("Testing auto-login and apply...\n")
    
    result = await _batch_apply_one(test_job.get("url"), test_job.get("title", ""), "Trabajando", None)
    
    print("\nResult:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
