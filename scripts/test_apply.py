import asyncio
import sys
import os
from collections import defaultdict
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

# Ensure we can import from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.job_service import search_jobs
from tools.auto_apply_tools import _batch_apply_one
from services.browser_client import stop_browser

async def main():
    print("Fetching profile...")
    # Get the AI-ingested profile (we assume it's ID 3 based on the previous output)
    # Let's just get the default profile to be safe.
    from database.repos import profiles as profile_repo
    profile = profile_repo.get_default_profile()
    if not profile:
        print("No default profile found.")
        return

    print(f"Using profile: {profile.get('personalInfo', {}).get('firstName')} (Skills: {len(profile.get('skills', []))})")
    print("Searching for entry level developer jobs across platforms...")
    
    # We use new engine to scrape all registered sites
    jobs = await search_jobs("Python Junior", location="Chile", remote_only=False, use_new_engine=True)
    
    # Group jobs by domain
    jobs_by_domain = defaultdict(list)
    for j in jobs:
        if not j.get("url"): continue
        domain = urlparse(j["url"]).netloc.replace("www.", "")
        jobs_by_domain[domain].append(j)

    print(f"\nFound jobs across {len(jobs_by_domain)} domains:")
    for domain, domain_jobs in jobs_by_domain.items():
        print(f"  - {domain}: {len(domain_jobs)} offers")

    # Pick 1 job from each domain
    test_jobs = []
    for domain, domain_jobs in jobs_by_domain.items():
        if "chiletrabajos" in domain:
            test_jobs.append(domain_jobs[0])

    print(f"\nStarting test application on {len(test_jobs)} unique sites...")
    
    for idx, job in enumerate(test_jobs, 1):
        domain = urlparse(job['url']).netloc.replace("www.", "")
        print(f"\n[{idx}/{len(test_jobs)}] Testing on {domain}...")
        print(f"Offer: {job['title']} @ {job['company']}")
        print(f"URL: {job['url']}")
        
        try:
            res = await _batch_apply_one(job['url'], profile)
            if res.get("success"):
                print(f"✅ SUCCESS applying on {domain}")
            else:
                print(f"❌ FAILED applying on {domain}: {res.get('error')}")
        except Exception as e:
            print(f"❌ CRITICAL ERROR applying on {domain}: {e}")

    print("\nClosing browser...")
    await stop_browser()
    print("Test complete.")

if __name__ == "__main__":
    asyncio.run(main())
