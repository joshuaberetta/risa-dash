"""
Render a product to PDF in headless Chromium. The worker opens the frontend's print
route, waits until every map reports it's idle, then prints. The PDF is what the
layout shows, with vector text. No GPU needed: WebGL runs on SwiftShader.
"""

import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.utils import timezone
from playwright.sync_api import sync_playwright

from . import storage
from .models import ProductVersion

log = logging.getLogger(__name__)

PAGE_MM = {"A3": (420, 297), "A4": (297, 210)}
CHROMIUM_ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist",
                 "--disable-dev-shm-usage", "--no-sandbox"]


def _print_pdf(url: str, w: int, h: int, out: str) -> None:
    """Runs on its own thread: Playwright's sync API keeps an event loop running,
    and Django won't touch the database from a thread that has one."""
    with sync_playwright() as p:
        browser = p.chromium.launch(args=CHROMIUM_ARGS)
        try:
            # Page in CSS px at 96 dpi; the map sets its own pixel ratio for 300 dpi
            page = browser.new_page(viewport={"width": round(w / 25.4 * 96), "height": round(h / 25.4 * 96)})
            page.on("console", lambda m: log.info("print console: %s", m.text))
            page.goto(url, wait_until="networkidle", timeout=120_000)
            page.wait_for_function("window.__printReady === true || typeof window.__printError === 'string'",
                                   timeout=180_000, polling=500)
            err = page.evaluate("window.__printError || null")
            if err:
                raise RuntimeError(f"Print page error: {err}")
            page.pdf(path=out, width=f"{w}mm", height=f"{h}mm", print_background=True,
                     prefer_css_page_size=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        finally:
            browser.close()


def render(version: ProductVersion) -> None:
    product = version.product
    w, h = PAGE_MM.get(product.page_size, PAGE_MM["A3"])
    url = f"{settings.PRINT_BASE_URL}/print/products/{product.id}?v={version.n}"
    site_slug = product.site.slug
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "product.pdf")
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(_print_pdf, url, w, h, out).result()
        code = (product.code or "RISA").replace(" ", "_")
        name = f"{code}_{site_slug}_v{version.n:02d}_{timezone.now():%Y%m%d}.pdf"
        version.pdf_key = storage.save(f"products/{product.id}/{name}", out, content_type="application/pdf")
    version.status = "ready"
    version.error = ""
    version.save(update_fields=["pdf_key", "status", "error"])
