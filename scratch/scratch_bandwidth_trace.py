import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        async def route_intercept(route):
            if route.request.resource_type in ["image", "media", "font", "stylesheet"]:
                await route.abort()
            else:
                await route.continue_()
                
        await page.route("**/*", route_intercept)
        
        total_bytes = 0
        async def on_response(response):
            nonlocal total_bytes
            try:
                body = await response.body()
                size = len(body)
                total_bytes += size
                if size > 100 * 1024:
                    print(f"[{size/1024:.0f} KB] {response.request.resource_type} - {response.url[:100]}")
            except:
                pass
                
        page.on("response", on_response)
        
        print("Visiting Threads...")
        try:
            await page.goto("https://www.threads.com/@harry950802/post/DXHDhcRErGs", wait_until="domcontentloaded", timeout=10000)
            await page.wait_for_function('() => document.querySelector("meta[property=\'og:title\']") !== null', timeout=3000)
            print("OG Title found!")
        except Exception as e:
            print("Error or timeout:", e)
            
        print(f"Total downloaded: {total_bytes / 1024 / 1024:.2f} MB")
        await browser.close()

asyncio.run(run())
