"""Browser check for the pilot gate. Usage: python3 measure.py OUTPUT_DIR

Needs Playwright and the Chromium it installed. Reads the admin cookie from mint_cookie.py.
"""
import os, subprocess, sys
from playwright.sync_api import sync_playwright
cookie = subprocess.run(["python3", "-I", os.path.join(os.path.dirname(os.path.abspath(__file__)), "mint_cookie.py"), "sushant@simula.no", "u_admin"], capture_output=True, text=True).stdout.strip()
name, value = cookie.split("=", 1)
with sync_playwright() as p:
    b = p.chromium.launch()
    for width in (1280, 390):
        pg = b.new_page(viewport={"width": width, "height": 900})
        pg.context.add_cookies([{"name": name, "value": value, "url": "http://localhost:8090/"}])
        pg.goto("http://localhost:8090/", wait_until="networkidle")
        info = pg.evaluate("""() => {
          const r = s => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect(); return [Math.round(b.left), Math.round(b.right), Math.round(b.top)]; };
          return { tabs: r('.tabs'), register: r('#tab-register'), actions: r('.tab-actions'), logout: r('#tab-logout'), admin: r('#tab-admin'), viewport: innerWidth, css: getComputedStyle(document.querySelector('.tabs')).display + ' / ' + getComputedStyle(document.querySelector('.tab-actions')).marginLeft };
        }""")
        print(width, info)
        pg.screenshot(path=f"{sys.argv[1]}/tabs-{width}.png", clip={"x": 0, "y": max(0, info["tabs"][2] - 20), "width": width, "height": 90})
    b.close()
