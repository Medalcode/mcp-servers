import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from services.auto_login import attempt_auto_login
from engines.selenium_engine import SeleniumEngine

async def main():
    print("Initializing browser engine...")
    engine = SeleniumEngine()
    
    url = "https://www.trabajando.cl/login"
    print(f"Navigating to {url}...")
    engine.navigate(url)
    
    async def caller(tool_name, args):
        func = getattr(engine, tool_name)
        # Call it synchronously but wrap it so attempt_auto_login can await
        return await asyncio.to_thread(func, **args)
        
    print("Testing auto-login on Trabajando.cl...")
    success = await attempt_auto_login(caller, url)
    
    if success:
        print("✅ Auto-login SUCCESS!")
    else:
        print("❌ Auto-login FAILED.")
        
    await asyncio.sleep(5)
    engine.close()

if __name__ == "__main__":
    asyncio.run(main())
