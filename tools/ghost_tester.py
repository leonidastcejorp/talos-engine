#!/usr/bin/env python3
"""
🔥 OPERATION: GHOST — Turnstile Bypass Tester
Tests if we can bypass Cloudflare Turnstile from this VPS
"""
import asyncio
import json
from playwright.async_api import async_playwright

async def test_turnstile():
    print("=" * 60)
    print("🔥 GHOST — Turnstile Bypass Tester")
    print("=" * 60)
    
    async with async_playwright() as p:
        # Launch with max stealth
        browser = await p.chromium.launch(
            headless=True,
            executable_path='/root/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome',
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-web-security',
                '--disable-features=BlockInsecurePrivateNetworkRequests',
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
                'Sec-Ch-Ua': '"Chromium";v="125", "Not.A/Brand";v="24"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
            },
            locale='en-US',
            timezone_id='Asia/Jakarta',
        )
        
        # Remove webdriver detection
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'id']
            });
            // Override chrome property
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({state: Notification.permission}) :
                originalQuery(parameters)
            );
        """)
        
        page = await context.new_page()
        
        # Test 1: Check our fingerprint
        print("\n📋 TEST 1: FINGERPRINT CHECK")
        fp = await page.evaluate("""
            () => ({
                webdriver: navigator.webdriver,
                plugins: navigator.plugins.length,
                languages: navigator.languages,
                userAgent: navigator.userAgent,
                chrome: typeof window.chrome !== 'undefined',
            })
        """)
        for k, v in fp.items():
            print(f"  {k}: {v}")
        
        # Test 2: Try Turnstile demo page
        print("\n📋 TEST 2: TURNSTILE DEMO")
        try:
            await page.goto('https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/b/turnstile', 
                           wait_until='networkidle', timeout=30000)
            content = await page.content()
            if 'turnstile' in content.lower():
                print("  ✅ Turnstile page loaded")
            else:
                print("  ⚠️ Page loaded but no Turnstile detected")
        except Exception as e:
            print(f"  ❌ Failed: {e}")
        
        # Test 3: Try real site with Turnstile
        test_sites = [
            ('cf-turnstile-demo', 'https://cf-turnstile-demo.pages.dev/'),
            ('nopecha demo', 'https://nopecha.com/demo/cloudflare'),
        ]
        
        print("\n📋 TEST 3: TURNSTILE SITES")
        for name, url in test_sites:
            try:
                print(f"\n  → Testing {name}...")
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(2)
                
                title = await page.title()
                print(f"  Title: {title}")
                
                # Check for iframe/turnstile widget
                has_turnstile = await page.evaluate("""
                    () => {
                        const iframes = document.querySelectorAll('iframe');
                        const turnstileIframes = Array.from(iframes).filter(
                            f => f.src && f.src.includes('turnstile')
                        );
                        return {
                            iframeCount: iframes.length,
                            turnstileIframes: turnstileIframes.length,
                            turnstileSrcs: turnstileIframes.map(f => f.src.substring(0, 100))
                        };
                    }
                """)
                print(f"  Turnstile detection: {json.dumps(has_turnstile)}")
                
                # Try clicking checkbox if present
                try:
                    checkbox = await page.wait_for_selector('#cf-turnstile-wrapper iframe', timeout=5000)
                    if checkbox:
                        print("  ✅ Turnstile widget found!")
                        frame = await checkbox.content_frame()
                        if frame:
                            print("  Got iframe content frame")
                except:
                    print("  ⚠️ No Turnstile widget found via selector")
                
            except Exception as e:
                print(f"  ❌ Error: {str(e)[:100]}")
        
        # Test 4: Try simple Turnstile solve
        print("\n📋 TEST 4: ATTEMPT TURNSTILE SOLVE")
        try:
            await page.goto('https://nopecha.com/demo/cloudflare', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)
            
            # Try to interact with the page
            page_source = await page.content()
            has_widget = 'cf-turnstile' in page_source or 'turnstile' in page_source.lower()
            print(f"  Cloudflare Turnstile detected: {has_widget}")
            
            # Screenshot
            await page.screenshot(path='/root/bounty_output/turnstile_test.png', full_page=True)
            print("  📸 Screenshot saved: /root/bounty_output/turnstile_test.png")
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:100]}")
        
        await browser.close()
        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_turnstile())
