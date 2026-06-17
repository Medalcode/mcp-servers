import asyncio
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from services.job_service import mass_register_sf

async def main():
    print("Testing mass registration on SuccessFactors...")
    urls = [
        "https://oportunidades.cencosud.com/"
    ]
    
    results = await mass_register_sf(urls)
    print("Registration Results:")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
