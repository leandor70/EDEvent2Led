"""
Test tour guide positioning for New Effect button step.
Tests that popover appears ABOVE the button in bottom sticky footer.
"""
import asyncio
from playwright.async_api import async_playwright

async def test_tour():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"[BROWSER] {msg.text}"))
        
        # Navigate to effects-editor
        print("[INFO] Navigating to effects-editor.html...")
        await page.goto('http://localhost:8000/effects-editor.html')
        
        # Wait for page to load
        await page.wait_for_load_state('networkidle')
        print("[INFO] Page loaded")
        
        # Wait for i18n to load and tour to initialize
        print("[INFO] Waiting for i18n and tour initialization...")
        await asyncio.sleep(3)
        
        # Check if tour started
        popover = await page.query_selector('[data-tour-popover]')
        
        if not popover:
            print("[INFO] Tour did not start automatically")
            
            # Check if completed
            completed = await page.evaluate("""
                async () => {
                    try {
                        const settings = await eel.get_settings()();
                        return settings.completed_guides || {};
                    } catch(e) {
                        return null;
                    }
                }
            """)
            print(f"[INFO] Completed guides: {completed}")
            
            # Try manual restart
            print("[INFO] Attempting manual restart...")
            await page.evaluate("window.restartTour()")
            await asyncio.sleep(2)
            
            popover = await page.query_selector('[data-tour-popover]')
            if not popover:
                print("[FAIL] Tour still not visible after manual restart")
                await browser.close()
                return
        
        print("[OK] Tour is active!")
        
        # Advance through steps until we reach the "New Effect" button step
        step_count = 0
        max_steps = 25  # Increased limit
        
        while step_count < max_steps:
            step_count += 1
            
            # Check current step target
            popover = await page.query_selector('[data-tour-popover]')
            if not popover:
                print(f"[INFO] Tour ended at step {step_count}")
                break
            
            # Get the target element ID
            target_attr = await popover.get_attribute('data-tour-target')
            print(f"[STEP {step_count}] Target: {target_attr}")
            
            # Check if this is the New Effect button step
            if target_attr == '#btn-new-effect':
                print(f"\n[OK] Found New Effect button step at step {step_count}!")
                
                # Wait for animations
                await asyncio.sleep(1)
                
                # Get button coordinates
                button = await page.query_selector('#btn-new-effect')
                if not button:
                    print("[ERROR] Button not found!")
                    break
                    
                button_box = await button.bounding_box()
                
                # Get popover coordinates
                popover_box = await popover.bounding_box()
                
                # Get viewport height
                viewport = page.viewport_size
                
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
                
                # Verify popover is ABOVE button
                popover_bottom = popover_box['y'] + popover_box['height']
                button_top = button_box['y']
                
                print(f"\nVerification:")
                print(f"  Popover bottom: {popover_bottom:.2f}px")
                print(f"  Button top:     {button_top:.2f}px")
                print(f"  Gap:            {button_top - popover_bottom:.2f}px")
                
                if popover_bottom < button_top:
                    print(f"\n  [OK] Popover is ABOVE button (gap: {button_top - popover_bottom:.2f}px)")
                else:
                    print(f"\n  [FAIL] Popover is NOT above button (overlap: {popover_bottom - button_top:.2f}px)")
                
                print("="*70)
                
                # Take screenshot
                screenshot_path = 'testimages/effects-tour-new-effect-button.png'
                await page.screenshot(path=screenshot_path, full_page=False)
                print(f"\n[OK] Screenshot saved: {screenshot_path}")
                
                # Wait a bit for inspection
                print("\n[INFO] Pausing for inspection (5 seconds)...")
                await asyncio.sleep(5)
                
                await browser.close()
                return
            
            # Click Next button to advance
            next_btn = await page.query_selector('[data-tour-action="next"]')
            if next_btn:
                await next_btn.click()
                await asyncio.sleep(0.8)  # Slightly longer delay for animations
            else:
                # Maybe it's the last step?
                done_btn = await page.query_selector('[data-tour-action="done"]')
                if done_btn:
                    print("[INFO] Reached last step (Done button visible)")
                    break
                else:
                    print("[INFO] No Next/Done button found")
                    break
        
        print(f"\n[INFO] Completed {step_count} steps without finding #btn-new-effect target")
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_tour())
