import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        total_bytes = 0
        
        async def on_response(response):
            nonlocal total_bytes
            try:
                # 讀這段如果出錯就略過 (比如說是 redirect)
                body = await response.body()
                total_bytes += len(body)
            except Exception as e:
                # Fallback to header
                try:
                    headers = await response.all_headers()
                    dl = headers.get("content-length")
                    if dl:
                        total_bytes += int(dl)
                except:
                    pass

        async def route_intercept(route):
            if route.request.resource_type in ["image", "media", "font", "stylesheet"]:
                await route.abort()
            else:
                await route.continue_()
                
        await page.route("**/*", route_intercept)
        page.on("response", on_response)
        
        print("Visiting Threads...")
        await page.goto("https://www.threads.com/@harry950802/post/DXHDhcRErGs", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        print(f"Total downloaded: {total_bytes / 1024 / 1024:.2f} MB")
        await browser.close()

asyncio.run(run())
