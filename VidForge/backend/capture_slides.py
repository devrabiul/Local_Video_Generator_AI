import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

SLIDES_DIR = Path("D:/AI/VidForge/presentation_slides")
SLIDES_DIR.mkdir(parents=True, exist_ok=True)

async def capture_all_slides():
    print("Launching Chrome for interactive slide capture...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--window-size=1920,1080"]
        )
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        print("Navigating to http://127.0.0.1:8700...")
        await page.goto("http://127.0.0.1:8700", wait_until="networkidle")
        await page.wait_for_timeout(2500)

        # Slide 1: Main Overview (Header, System Badges, Hero)
        print("Capturing Slide 1: Overview...")
        await page.screenshot(path=str(SLIDES_DIR / "slide1_overview.png"))

        # Slide 2: Format & Dynamic Pacing Controls
        print("Capturing Slide 2: Dynamic Pacing & Formats...")
        # Scroll slightly to bring formats and slider into view
        await page.evaluate("window.scrollTo({top: 180, behavior: 'smooth'})")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SLIDES_DIR / "slide2_formats_pacing.png"))

        # Slide 3: Quick Inspirations expanded
        print("Capturing Slide 3: Quick Inspirations...")
        insp_btn = page.locator("button:has-text('Quick Inspirations')")
        if await insp_btn.count() > 0:
            await insp_btn.first.click()
            await page.wait_for_timeout(1200)
        await page.screenshot(path=str(SLIDES_DIR / "slide3_inspirations.png"))

        # Slide 4: Multi-Engine Voice Studio & Aspect Ratio
        print("Capturing Slide 4: Voice Studio...")
        await page.evaluate("window.scrollTo({top: 550, behavior: 'smooth'})")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SLIDES_DIR / "slide4_voices.png"))

        # Slide 5: Ollama Story Studio Tab
        print("Capturing Slide 5: Ollama Story Studio...")
        tab_btn = page.locator("button:has-text('Ollama Story Studio')")
        if await tab_btn.count() > 0:
            await tab_btn.first.click()
            await page.wait_for_timeout(1500)
        await page.screenshot(path=str(SLIDES_DIR / "slide5_story_studio.png"))

        # Slide 6: Switch back to Production Studio and view right panel (Queue & Pipeline)
        print("Capturing Slide 6: Production Pipeline & Queue...")
        prod_tab = page.locator("button:has-text('Production Studio')")
        if await prod_tab.count() > 0:
            await prod_tab.first.click()
            await page.wait_for_timeout(1000)
        await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SLIDES_DIR / "slide6_pipeline.png"))

        # Slide 7: Video Preview & Player view
        print("Capturing Slide 7: Live Video Player...")
        await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SLIDES_DIR / "slide7_player.png"))

        await browser.close()
        print("All slides successfully captured!")

if __name__ == "__main__":
    asyncio.run(capture_all_slides())
