"""Screenshots for the user guide (frontend/public/guide/static/shots/), in the worker's
headless Chromium against the dev app, like scripts/shot.py. Needs the sample response
(scripts/seed_sample.py) and its edit key. It makes a bundle and imports it back into the
same response, which changes nothing.

    docker compose exec -T -e SLUG=<response> -e KEY=<edit-key> worker python - < scripts/guide-shots.py
    docker compose cp worker:/tmp/shots/. frontend/public/guide/static/shots/

ONLY=bundle,bundle-import takes some of them. "landing", "summary", "products", "ai",
"product" and "page2" need the demo
response (seed_sample.py --demo: SLUG=demo, its key), "page2" with page 2 turned on. The guide's other shots (the site, a
feature with its Kobo photo, the Kobo dialog, the summary, the data table and the page 1
editor) were taken by hand from the sample with the box's demo Kobo project
(kobo-in-a-box remote/risa/demo-kobo.py) connected.
"""
import os
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://host.docker.internal:5173")
API = os.environ.get("API", "http://web:8000")
SLUG, KEY = os.environ["SLUG"], os.environ["KEY"]
ONLY = set(filter(None, os.environ.get("ONLY", "").split(",")))
OUT = Path("/tmp/shots")


def shot(page, name):
    page.wait_for_timeout(600)
    page.screenshot(path=str(OUT / f"{name}.jpg"), type="jpeg", quality=85)
    print("wrote", name)


def want(name):
    return not ONLY or name in ONLY


def main():
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--no-sandbox"])
        page = b.new_page(viewport={"width": 1440, "height": 900})
        page.goto(BASE + "/")
        # Walkthroughs off: they start by themselves on a first visit
        page.evaluate("([s, k]) => { localStorage.setItem('risa-edit-key:' + s, k);"
                      " for (const n of ['home', 'response', 'site']) localStorage.setItem('risa-tour-seen:' + n, '1') }",
                      [SLUG, KEY])

        if want("new-response"):
            page.goto(BASE + "/", wait_until="networkidle")
            page.get_by_role("button", name="New response").click()
            page.get_by_label("Name").fill("Venezuela: earthquake, June 2026")
            page.get_by_label("Country (ISO3)").fill("VEN")
            page.get_by_label("GLIDE number").fill("EQ-2026-000093-VEN")
            shot(page, "new-response")

        if want("landing") or want("summary") or want("products"):
            site = __import__("json").loads(urllib.request.urlopen(f"{API}/api/responses/{SLUG}").read())
            page.goto(f"{BASE}/r/{SLUG}/{site['sites'][0]['slug']}", wait_until="networkidle")
            page.wait_for_timeout(6000)
            if want("landing"):
                shot(page, "landing")
            if want("summary"):
                # The side panel alone, at twice the size, scrolled whole
                hi = b.new_page(viewport={"width": 1440, "height": 1800}, device_scale_factor=2)
                hi.goto(BASE + "/")
                hi.evaluate("([s, k]) => { localStorage.setItem('risa-edit-key:' + s, k);"
                            " for (const n of ['home', 'response', 'site']) localStorage.setItem('risa-tour-seen:' + n, '1') }", [SLUG, KEY])
                hi.goto(f"{BASE}/r/{SLUG}/{site['sites'][0]['slug']}", wait_until="networkidle")
                hi.wait_for_timeout(4000)
                box = hi.locator("[data-tour=summary]").bounding_box()
                hi.screenshot(path=str(OUT / "summary.jpg"), type="jpeg", quality=85,
                              clip={"x": box["x"], "y": box["y"] - 40, "width": box["width"], "height": box["height"] + 90})
                print("wrote summary")
                hi.close()
            if want("products"):
                page.get_by_role("button", name="Products").first.click()
                page.wait_for_timeout(2500)
                shot(page, "products")

        if want("ai"):
            site = urllib.request.urlopen(f"{API}/api/responses/{SLUG}").read()
            site_slug = __import__("json").loads(site)["sites"][0]["slug"]
            page.goto(f"{BASE}/r/{SLUG}/{site_slug}", wait_until="networkidle")
            page.get_by_role("tab", name="AI analysis").click()
            page.wait_for_timeout(6000)
            shot(page, "ai")

        if want("product") or want("page2"):
            # The demo's product, with page 2 on: page 1's tab, then page 2's, each previewed
            site = __import__("json").loads(urllib.request.urlopen(f"{API}/api/responses/{SLUG}").read())
            page.goto(f"{BASE}/r/{SLUG}/{site['sites'][0]['slug']}", wait_until="networkidle")
            page.locator(".layer-row a").first.click()
            page.wait_for_timeout(1500)
            if want("product"):
                page.get_by_role("button", name="Update preview").click()
                page.wait_for_timeout(25000)
                page.get_by_role("button", name="Page 1", exact=True).click(timeout=2000) if page.get_by_role(
                    "button", name="Page 1", exact=True).count() else None
                # The editor's fields from the top, with its tabs
                page.get_by_role("dialog").locator(".mantine-ScrollArea-viewport").first.evaluate("e => e.scrollTo(0, 0)")
                page.wait_for_timeout(1500)
                shot(page, "product")
            if want("page2"):
                page.get_by_role("tab", name="Page 2 · findings").click()
                page.wait_for_timeout(1500)
                if page.get_by_text("Page 2", exact=True).count():
                    page.get_by_text("Page 2", exact=True).last.click()
                page.wait_for_timeout(2500)
                shot(page, "page2")
            page.keyboard.press("Escape")

        bundle = "/tmp/sample.risa.zip"
        if want("bundle") or want("bundle-import"):
            page.goto(f"{BASE}/r/{SLUG}", wait_until="networkidle")
            page.get_by_role("button", name="Bundle").click()
            page.get_by_role("button", name="Make bundle").click()
            page.get_by_text("Making…").wait_for()
            page.get_by_text("Making…").wait_for(state="detached", timeout=180_000)
            link = page.get_by_text("Download,").first
            if want("bundle"):
                shot(page, "bundle")
            urllib.request.urlretrieve(API + link.locator("xpath=ancestor::a").get_attribute("href"), bundle)

        if want("bundle-import"):
            page.goto(BASE + "/", wait_until="networkidle")
            page.get_by_role("button", name="Import bundle").click()
            page.locator("input[type=file]").set_input_files(bundle)
            page.get_by_label("Edit key (if the response is already here)").fill(KEY)
            page.get_by_role("button", name="Import", exact=True).click()
            page.get_by_text("Updated").or_(page.get_by_text("Import failed")).first.wait_for(timeout=180_000)
            shot(page, "bundle-import")
        b.close()


if __name__ == "__main__":
    main()
