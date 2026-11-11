"""
Debug tour guide - check why tour doesn't start.
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_tour():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # Navigate to effects-editor
        print("[INFO] Navigating to effects-editor.html...")
        await page.goto('http://localhost:8000/web/effects-editor.html')
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(3)
        
        # Check if page loaded
        title = await page.title()
        print(f"[INFO] Page title: {title}")
        
        # Check for tour guide script
        has_tour_guide = await page.evaluate("""
            () => typeof window.TourGuide !== 'undefined'
        """)
        print(f"[INFO] TourGuide defined: {has_tour_guide}")
        
        # Check completed guides from settings
        completed_guides = await page.evaluate("""
            async () => {
                const response = await fetch('http://localhost:8000/api/get_settings');
                const data = await response.json();
                return data.completed_guides || {};
            }
        """)
        print(f"[INFO] Completed guides: {completed_guides}")
        
        # Check if popover exists
        popover = await page.query_selector('[data-tour-popover]')
        print(f"[INFO] Popover element exists: {popover is not None}")
        
        # Check if tour is active
        tour_active = await page.evaluate("""
            () => {
                if (typeof window.activeTour !== 'undefined' && window.activeTour) {
                    return {
                        guideId: window.activeTour.guideId,
                        currentStep: window.activeTour.currentStep,
                        totalSteps: window.activeTour.steps.length
                    };
                }
                return null;
            }
        """)
        print(f"[INFO] Active tour: {tour_active}")
        
        # Try to manually start tour
        print("\n[INFO] Attempting to manually start tour...")
        try:
            result = await page.evaluate("""
                () => {
                    if (typeof startEffectsEditorGuide === 'function') {
                        startEffectsEditorGuide();
                        return 'Started';
                    }
                    return 'Function not found';
                }
            """)
            print(f"[INFO] Manual start result: {result}")
            await asyncio.sleep(2)
            
            # Check again
            popover = await page.query_selector('[data-tour-popover]')
            print(f"[INFO] Popover after manual start: {popover is not None}")
            
        except Exception as e:
            print(f"[ERROR] Failed to start tour: {e}")
        
        # Wait for inspection
        print("\n[INFO] Browser open for inspection. Press Ctrl+C to close...")
        try:
            await asyncio.sleep(60)
        except KeyboardInterrupt:
            pass
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(debug_tour())
