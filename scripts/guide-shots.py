"""Screenshots for the user guide (frontend/public/guide/static/shots/), in the worker's
headless Chromium against the dev app, like scripts/shot.py. Needs the sample response
(scripts/seed_sample.py) and its edit key. It makes a bundle and imports it back into the
same response, which changes nothing.

    docker compose exec -T -e SLUG=<response> -e KEY=<edit-key> worker python - < scripts/guide-shots.py
    docker compose cp worker:/tmp/shots/. frontend/public/guide/static/shots/

ONLY=bundle,bundle-import takes some of them. The guide's other shots (the site, a
feature with its Kobo photo, the Kobo dialog, the summary, the data table, AI analysis
and the page 1 editor) were taken by hand from the sample with the box's demo Kobo project
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
        b = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--no-sandbox"])
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
