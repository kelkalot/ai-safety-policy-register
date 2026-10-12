"""Browser check for the pilot gate. Usage: python3 shot.py OUTPUT_DIR

Needs Playwright and the Chromium it installed. Reads the admin cookie from mint_cookie.py.
"""
import os, subprocess, sys
from playwright.sync_api import sync_playwright
out = subprocess.run(["python3", "-I", os.path.join(os.path.dirname(os.path.abspath(__file__)), "mint_cookie.py"), "sushant@simula.no", "u_admin"], capture_output=True, text=True).stdout.strip()
name, value = out.split("=", 1)
EXE = "/home/sushant/.cache/ms-playwright/chromium-1181/chrome-linux/chrome"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=EXE)
    for url, tag in (("http://localhost:8090/", "main"), ("http://localhost:8090/admin/", "admin")):
        pg = b.new_page(viewport={"width": 1100, "height": 760})
        pg.context.add_cookies([{"name": name, "value": value, "url": "http://localhost:8090/"}])
        pg.goto(url, wait_until="load", timeout=30000)
        pg.wait_for_timeout(600)
        pg.screenshot(path=f"{sys.argv[1]}/{tag}.png", full_page=False)
        print(tag, pg.evaluate("() => [document.querySelector('.masthead') && getComputedStyle(document.querySelector('.masthead')).backgroundColor, getComputedStyle(document.body).backgroundColor, document.querySelectorAll('#rows tr').length]"))
    b.close()
