import discord
from discord.ext import commands
import os
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# 偽裝的 User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 建立繼承自 commands.Bot 的自訂類別來管理全域 Playwright 生命週期
class PreviewBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        self.playwright = None
        self.browser = None

    async def setup_hook(self):
        # 啟動時自動初始化 Playwright，不要每次收到訊息才重開瀏覽器
        print("啟動背景 Playwright 瀏覽器...")
        self.playwright = await async_playwright().start()
        # 啟動 Headless Chromium
        self.browser = await self.playwright.chromium.launch(headless=True)
        print("Playwright 準備完畢！")

    async def close(self):
        # 關閉機器人時自動清理背景瀏覽器
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        await super().close()

bot = PreviewBot()

@bot.event
async def on_ready():
    print(f'機器人已上線：{bot.user.name} (ID: {bot.user.id})')
    print('------')

async def fetch_og_data_fast(url: str) -> dict:
    """極速版 Playwright 抓取，重用瀏覽器並阻擋不必要的資源。"""
    try:
        # 直接使用全域開啟的 browser 開新分頁 (非常快，省去幾秒啟動時間)
        context = await bot.browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()

        # 攔截並阻擋字體和樣式表載入 (不阻擋 media 防止影片元件崩潰)
        async def route_intercept(route):
            if route.request.resource_type in ["font", "stylesheet"]:
                await route.abort()
            else:
                await route.continue_()
        
        await page.route("**/*", route_intercept)

        try:
            # wait_until="domcontentloaded" 比原本的 "networkidle" 快非常多
            await page.goto(url, timeout=10000, wait_until="domcontentloaded")
            
            # 主動等待 `og:title` 或 `twitter:title` 被 JS 注入 DOM 中
            await page.wait_for_function(
                """() => document.querySelector("meta[property='og:title']") !== null || 
                         document.querySelector("meta[name='twitter:title']") !== null ||
                         document.querySelector("meta[name='title']") !== null""",
                timeout=3000
            )
            
            # [關鍵修復] React 渲染內文的影片播放器比較慢
            # 這裡主動多等一下 <video> 標籤出現 (最高等 3.5 秒)
            try:
                await page.wait_for_selector("video", timeout=3500)
            except:
                pass

        except Exception as e:
            # 即使超時，如果部分結構出來了我們依舊可以嘗試提取
            pass
            
        html = await page.content()
        await context.close()
        
        soup = BeautifulSoup(html, 'html.parser')
        og_data = {}
        
        # 提取標題
        og_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "twitter:title"}) or soup.find("meta", attrs={"name": "title"})
        if og_title and og_title.get("content"):
            og_data["title"] = og_title["content"]
        else:
            og_data["title"] = soup.title.string if soup.title else ""
        
        # 提取描述
        og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"name": "twitter:description"})
        if og_desc and og_desc.get("content"):
            og_data["description"] = og_desc["content"]
            
        # 提取圖片
        og_image = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if og_image and og_image.get("content"):
            og_data["image"] = og_image["content"]

        # 提取網站名稱
        og_site_name = soup.find("meta", property="og:site_name")
        if og_site_name and og_site_name.get("content"):
            og_data["site_name"] = og_site_name["content"]
            
        return og_data if og_data.get("title") else None
    except Exception as e:
        print(f"抓取 {url} 時發生嚴重錯誤: {e}")
        return None

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    content = message.content
    # 限制只對 Threads 網址有反應
    url_pattern = r'(https?://(?:www\.)?threads\.(?:net|com)[^\s]+)'
    urls = re.findall(url_pattern, content)
    
    if urls:
        embeds_to_send = []
        loading_msg = await message.reply("⚡ 正在極速抓取預覽...")

        for url in urls:
            url = url.strip(".,;:?!)([]{}")
            og_data = await fetch_og_data_fast(url)
            
            if og_data:
                title = og_data.get("title", "無法取得標題")
                
                if "site_name" in og_data:
                    title = f"[{og_data['site_name']}] {title}"
                
                if len(title) > 256:
                    title = title[:253] + "..."
                    
                description = og_data.get("description", "")
                if len(description) > 4096:
                    description = description[:4093] + "..."

                embed = discord.Embed(
                    title=title,
                    url=url,
                    description=description,
                    color=discord.Color.brand_green()
                )
                
                if "image" in og_data:
                    embed.set_image(url=og_data["image"])
                
                embeds_to_send.append(embed)
                
        # 刪除 loading
        try:
            await loading_msg.delete()
        except:
            pass
        
        # 發送最終預覽
        if embeds_to_send:
            try:
                await message.reply(content="👀 網頁預覽", embeds=embeds_to_send[:10], mention_author=False)
            except Exception as e:
                print(f"發送預覽卡片時失敗: {e}")

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("錯誤：無法在 .env 檔案中找到 DISCORD_TOKEN。")