import asyncio
import sys
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

async def test():
    url = "https://www.threads.com/@tsukinomori__msr/post/DXOqsrUiRT6?xmt=AQF0qXVHn-cchE_HcbEVjl_1dPu1vQZdi4kG2jTBLjxvIw"
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0")
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_selector("video", timeout=4000)
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            og_img = soup.find("meta", property="og:image")
            print("og:image =", og_img.get("content") if og_img else None)
            
            videos = soup.find_all("video")
            print(f"找到 {len(videos)} 個 video 標籤")
            
            for i, v in enumerate(videos):
                print(f"--- Video {i+1} ---")
                print("src:", v.get("src")[:80] + "...")
                print("poster:", str(v.get("poster"))[:100])
                print("classes:", v.get("class"))
                print("autoPlay:", v.get("autoplay"))
                # 印出往上找的幾個 parent，看看有沒有明顯的 post 特徵
                curr = v
                depth = 0
                while curr and depth < 5:
                    curr = curr.parent
                    if curr and curr.name != '[document]':
                        print(f"  Parent {depth+1} <{curr.name}> classes: {curr.get('class')}")
                    depth += 1
                    
            await browser.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
