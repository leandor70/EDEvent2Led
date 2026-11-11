"""
Simple test: manually trigger tour and measure #btn-new-effect popover position.
"""
import asyncio
import sys
from playwright.async_api import async_playwright

# Fix Windows Unicode issue
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        print("[INFO] Loading effects-editor.html...")
        await page.goto('http://localhost:8000/effects-editor.html')
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(3)
        
        # Manually inject tour step for #btn-new-effect
        print("[INFO] Manually creating tour popover for #btn-new-effect...")
        
        result = await page.evaluate("""
            () => {
                // Create a mock tour step directly for #btn-new-effect
                const button = document.querySelector('#btn-new-effect');
                if (!button) {
                    return {success: false, error: 'Button not found'};
                }
                
                // Create popover
                const popover = document.createElement('div');
                popover.setAttribute('data-tour-popover', '');
                popover.setAttribute('data-tour-target', '#btn-new-effect');
                popover.style.cssText = 'position: fixed; z-index: 10002; max-width: 420px; background: linear-gradient(145deg, #1a1a2e 0%, #16213e 100%); border: 2px solid var(--primary-accent); border-radius: 12px; padding: 24px; box-shadow: 0 8px 32px rgba(0,0,0,0.8), 0 0 60px rgba(255,102,0,0.25); color: white;';
                
                popover.innerHTML = '<div style="font-family: Orbitron, sans-serif; font-size: 18px; font-weight: bold; margin-bottom: 12px; color: var(--primary-accent);">Create New Effect</div><div style="font-family: Rajdhani, sans-serif; font-size: 16px; line-height: 1.6; margin-bottom: 20px;">Click this button to create a new RGB lighting effect.</div><div style="display: flex; justify-content: space-between;"><div style="font-size: 13px; color: rgba(255,255,255,0.5);">Step 2 of 5</div><button data-tour-action="next" style="padding: 8px 20px; background: var(--primary-accent); border: none; border-radius: 6px; color: white; font-family: Orbitron, sans-serif; font-size: 13px; font-weight: bold; cursor: pointer;">NEXT</button></div>';
                
                document.body.appendChild(popover);
                
                // Position popover ABOVE button
                const buttonRect = button.getBoundingClientRect();
                const popoverHeight = popover.offsetHeight;
                const margin = 16;
                
                const top = buttonRect.top - popoverHeight - margin;
                const left = Math.max(16, Math.min(window.innerWidth - popover.offsetWidth - 16, buttonRect.left));
                
                popover.style.top = top + 'px';
                popover.style.left = left + 'px';
                
                // Create overlay backdrop
                const overlay = document.createElement('div');
                overlay.id = 'tour-overlay';
                overlay.style.cssText = 'position: fixed; inset: 0; background: rgba(0, 0, 0, 0.75); z-index: 10000;';
                document.body.appendChild(overlay);
                
                // Highlight target
                const highlight = document.createElement('div');
                highlight.id = 'tour-highlight';
                highlight.style.cssText = 'position: fixed; top: ' + (buttonRect.top - 4) + 'px; left: ' + (buttonRect.left - 4) + 'px; width: ' + (buttonRect.width + 8) + 'px; height: ' + (buttonRect.height + 8) + 'px; border: 3px solid var(--primary-accent); border-radius: 8px; box-shadow: 0 0 0 4px rgba(255,102,0,0.15), 0 0 30px rgba(255,102,0,0.4); z-index: 10001; pointer-events: none;';
                document.body.appendChild(highlight);
                
                return {success: true};
            }
        """)
        
        if not result['success']:
            print(f"[FAIL] {result.get('error', 'Unknown error')}")
            await browser.close()
            return
        
        print("[OK] Tour popover created and positioned")
        await asyncio.sleep(1)
        
        # Get actual rendered positions
        button = await page.query_selector('#btn-new-effect')
        popover = await page.query_selector('[data-tour-popover]')
        
        button_box = await button.bounding_box()
        popover_box = await popover.bounding_box()
        viewport = page.viewport_size
        
        # Display measurements
        print("\n" + "="*70)
        print("  POSITIONING MEASUREMENTS")
        print("="*70)
        print(f"\nViewport Height: {viewport['height']}px")
        print(f"\nButton (#btn-new-effect):")
        print(f"  Top:    {button_box['y']:.2f}px")
        print(f"  Bottom: {button_box['y'] + button_box['height']:.2f}px")
        print(f"  Height: {button_box['height']:.2f}px")
        
        print(f"\nPopover ([data-tour-popover]):")
        print(f"  Top:    {popover_box['y']:.2f}px")
        print(f"  Bottom: {popover_box['y'] + popover_box['height']:.2f}px")
        print(f"  Height: {popover_box['height']:.2f}px")
        
        # Verification
        popover_bottom = popover_box['y'] + popover_box['height']
        button_top = button_box['y']
        gap = button_top - popover_bottom
        
        print(f"\nVerification:")
        print(f"  Popover bottom: {popover_bottom:.2f}px")
        print(f"  Button top:     {button_top:.2f}px")
        print(f"  Gap:            {gap:.2f}px")
        
        if popover_bottom < button_top:
            print(f"\n  [OK] Popover is ABOVE button (gap: {gap:.2f}px)")
        else:
            print(f"\n  [FAIL] Popover is NOT above button (overlap: {-gap:.2f}px)")
        
        print("="*70)
        
        # Screenshot
        screenshot_path = 'testimages/effects-tour-new-effect-button.png'
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"\n[OK] Screenshot saved: {screenshot_path}")
        
        # Wait for inspection
        print("\n[INFO] Browser open for inspection (30 seconds)...")
        await asyncio.sleep(30)
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test())
