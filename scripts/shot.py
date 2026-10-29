"""Screenshot a page of the dev app in the worker's headless Chromium (no GPU, like printing).

    docker compose exec -T -e URL=/r/<response>/<site> -e KEY=<edit-key> -e SLUG=<response> worker \
        python - < scripts/shot.py && docker compose cp worker:/tmp/shot.png /tmp/shot.png
"""
import os

from playwright.sync_api import sync_playwright

base = os.environ.get("BASE", "http://host.docker.internal:5173")
url = base + os.environ.get("URL", "/")
w, h = (int(x) for x in os.environ.get("SIZE", "1440x900").split("x"))
with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--no-sandbox"])
    page = b.new_page(viewport={"width": w, "height": h})
    logs = []
    page.on("console", lambda m: logs.append(f"{m.type}: {m.text}"))
    page.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
    if os.environ.get("KEY"):
        page.goto(base + "/")
        page.evaluate("([s, k]) => localStorage.setItem('risa-edit-key:' + s, k)", [os.environ["SLUG"], os.environ["KEY"]])
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(int(os.environ.get("WAIT", "6000")))
    if os.environ.get("CLICK"):
        page.mouse.click(*(int(v) for v in os.environ["CLICK"].split(",")))
        page.wait_for_timeout(1500)
    page.screenshot(path="/tmp/shot.png")
    b.close()
for line in logs[-25:]:
    print(line)
