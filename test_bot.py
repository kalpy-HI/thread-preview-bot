import asyncio
import sys
from bot import PreviewBot, fetch_og_data_fast, bot

sys.stdout.reconfigure(encoding='utf-8')

async def test():
    # Setup playwright globally
    await bot.setup_hook()
    
    url = "https://www.threads.com/@tsukinomori__msr/post/DXOqsrUiRT6?xmt=AQF0qXVHn-cchE_HcbEVjl_1dPu1vQZdi4kG2jTBLjxvIw"
    print(f"Testing URL: {url}")
    result = await fetch_og_data_fast(url)
    
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    await bot.close()

if __name__ == "__main__":
    asyncio.run(test())
