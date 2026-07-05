import asyncio
from api_server import bg_batch_apply

async def main():
    try:
        await bg_batch_apply("test-id", ["trainee"], 5)
    except Exception:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
