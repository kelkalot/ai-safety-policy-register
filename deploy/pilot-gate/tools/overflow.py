"""Browser check for the pilot gate. Usage: python3 overflow.py OUTPUT_DIR

Needs Playwright and the Chromium it installed. Reads the admin cookie from mint_cookie.py.
"""
import os, subprocess, sys
from playwright.sync_api import sync_playwright
out = subprocess.run(["python3", "-I", os.path.join(os.path.dirname(os.path.abspath(__file__)), "mint_cookie.py"), "sushant@simula.no", "u_admin"], capture_output=True, text=True).stdout.strip()
name, value = out.split("=", 1)
JS = """() => {
  const vw = document.documentElement.clientWidth;
  const wide = [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.right > vw + 1 && r.width > 0; })
    .slice(0, 6).map(e => e.tagName + '.' + (e.className || e.id) + ' right=' + Math.round(e.getBoundingClientRect().right));
  return { vw, scrollW: document.documentElement.scrollWidth, wide };
}"""
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/home/sushant/.cache/ms-playwright/chromium-1181/chrome-linux/chrome")
    for w in (390, 1100):
        pg = b.new_page(viewport={"width": w, "height": 800})
        pg.context.add_cookies([{"name": name, "value": value, "url": "http://localhost:8090/"}])
        pg.goto("http://localhost:8090/admin/", wait_until="load", timeout=30000)
        pg.wait_for_timeout(800)
        print(w, pg.evaluate(JS))
        pg.screenshot(path=f"{sys.argv[1]}/admin-{w}.png", full_page=True)
        pg.close()
    b.close()
