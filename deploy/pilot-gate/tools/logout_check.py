"""Browser check for the pilot gate. Usage: python3 logout_check.py OUTPUT_DIR

Needs Playwright and the Chromium it installed. Reads the admin cookie from mint_cookie.py.
"""
import os, subprocess, sys
from playwright.sync_api import sync_playwright
out = subprocess.run(["python3", "-I", os.path.join(os.path.dirname(os.path.abspath(__file__)), "mint_cookie.py"), "sushant@simula.no", "u_admin"], capture_output=True, text=True).stdout.strip()
name, value = out.split("=", 1)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/home/sushant/.cache/ms-playwright/chromium-1181/chrome-linux/chrome")
    for who, cookie in (("admin", value), ("anon", None)):
        pg = b.new_page(viewport={"width": 1100, "height": 500})
        if cookie: pg.context.add_cookies([{"name": name, "value": cookie, "url": "http://localhost:8090/"}])
        pg.goto("http://localhost:8090/", wait_until="load", timeout=30000)
        pg.wait_for_timeout(800)
        print(who, "| logout visible:", pg.is_visible("#tab-logout"), "| admin visible:", pg.is_visible("#tab-admin"))
        pg.close()
    b.close()
