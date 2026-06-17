import asyncio
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.scrapers.sonda import scan_sonda

async def main():
    print("Scanning Sonda for Python jobs...")
    jobs = await scan_sonda("Python", "Chile")
    print(f"Found {len(jobs)} jobs:")
    print(json.dumps(jobs, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
