#!/usr/bin/env python3
"""Offline job search + apply script. Uses services directly (no MCP)."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.browser_client import call_tool, stop_browser, ensure_browser
from database.repos import profiles as profile_repo

async def safe_call(tool, args=None):
    result = await call_tool(tool, args or {})
    if result and ("failed after" in result or "error:" in result.lower()[:50]):
        print(f"  ⚠️ {result[:100]}")
        return ""
    return result or ""

async def main():
    await ensure_browser()
    profile = profile_repo.get_default_profile()
    if not profile:
        print("❌ No profile found")
        return
    print(f"✅ Profile loaded: {profile.get('name', profile.get('nombre', 'unknown'))}")

    # Discover jobs on each platform
    jobs = []
    
    # === SEARCH ===
    print("\n=== SEARCHING JOBS ===")
    
    # GetOnBoard - scraping via browser
    print("\n--- GetOnBoard: checking... ---")
    body = await safe_call("navigate", {"url": "https://www.getonbrd.com/jobs?q=trainee+intern+practica+junior&location=Chile"})
    if body:
        print(f"  GetOnBoard loaded ({len(body)} chars)")
        links = await safe_call("links", {})
        if links:
            print(f"  Found links")
    
    # FirstJob 
    print("\n--- FirstJob: checking... ---")
    body = await safe_call("navigate", {"url": "https://firstjob.me/oportunidades"})
    if body:
        print(f"  FirstJob loaded ({len(body)} chars)")

    # Search for specific jobs
    print("\n--- Searching 'trainee' on Google ---")
    await safe_call("navigate", {"url": "https://www.google.com/search?q=trainee+intern+practica+informatica+Chile+2026&hl=es"})
    
    text = await safe_call("run_script", {"script": "return document.body.innerText"})
    if text:
        # Extract job links
        print(f"  Search results ({len(text)} chars)")
        print(f"  Preview: {text[:500]}")

    print("\n=== DONE ===")
    await stop_browser()

if __name__ == "__main__":
    asyncio.run(main())
