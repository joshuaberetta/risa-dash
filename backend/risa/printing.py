"""
Print a product: headless Chromium renders only the map (and the locator maps) at
the frame's exact size, and Typst lays out the page around them (risa/typst/page1.typ).
Vector text, a JPEG map, and a layout shared with our other Typst documents.

No GPU needed: WebGL runs on SwiftShader. Nothing here needs the internet beyond what
the map itself loads, so it works on an offline box.
"""

import base64
import json
import logging
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from playwright.sync_api import sync_playwright

from . import page1, storage
from .models import Product, ProductVersion
from .summary import site_summary

log = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "typst"
CHROMIUM_ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist",
                 "--disable-dev-shm-usage", "--no-sandbox"]
PRINT_DPI = 300
DRAFT_DPI = 110
CSS_PX_PER_MM = 96 / 25.4


def _shoot(page, url: str, out: str, timeout_s: int = 180) -> dict:
    page.goto(url, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_function("window.__printReady === true || typeof window.__printError === 'string'",
                           timeout=timeout_s * 1000, polling=300)
    err = page.evaluate("window.__printError || null")
    if err:
        raise RuntimeError(f"Map page error: {err}")
    state = page.evaluate("window.__mapState || null")
    # The map's own canvas (preserveDrawingBuffer), not a page screenshot
    data_url = page.evaluate("window.__mapImage()")
    with open(out, "wb") as f:
        f.write(base64.b64decode(data_url.split(",", 1)[1]))
    return state


def _render_maps(product_id: str, version_n: int | None, frames: dict, dpi: int, tmp: str) -> dict:
    """Runs on its own thread: Playwright's sync API keeps an event loop running,
    and Django won't touch the database from a thread that has one."""
    base = f"{settings.PRINT_BASE_URL}/print/map/{product_id}"
    v = f"&v={version_n}" if version_n else ""
    mw, mh = frames["map"]
    loc = frames["locators"]

    def locator(browser, f: dict, url: str, out: str) -> dict | None:
        ctx = browser.new_context(viewport={"width": round(f["w"] * CSS_PX_PER_MM), "height": round(f["h"] * CSS_PX_PER_MM)},
                                  device_scale_factor=max(2, dpi / 96))
        try:
            return _shoot(ctx.new_page(), url, os.path.join(tmp, out), timeout_s=60) or {}
        except Exception:
            # The page still prints without it (e.g. no basemap offline)
            log.warning("Locator %s failed for %s", out, product_id, exc_info=True)
            return None
        finally:
            ctx.close()

    with sync_playwright() as p:
        browser = p.chromium.launch(args=CHROMIUM_ARGS)
        try:
            ctx = browser.new_context(viewport={"width": round(mw * CSS_PX_PER_MM), "height": round(mh * CSS_PX_PER_MM)},
                                      device_scale_factor=dpi / 96)
            page = ctx.new_page()
            page.on("console", lambda m: log.info("map: %s", m.text) if m.type in ("error", "warning") else None)
            state = _shoot(page, f"{base}?part=main{v}", os.path.join(tmp, "map.jpg"))
            ctx.close()
            fmt = lambda b: ",".join(f"{x:.6f}" for x in b)  # noqa: E731
            mark, centre = state["bounds"], f"{(state['bounds'][0] + state['bounds'][2]) / 2:.6f},{state['lat']:.6f}"
            if loc["area"]:
                area = locator(browser, loc["area"], f"{base}?part=inset&bounds={fmt(mark)}&zoom={state['zoom']:.2f}{v}", "inset.jpg")
                # The overview marks the area locator's extent, so the leader lines join them
                if area and area.get("bounds"):
                    mark = area["bounds"]
            if loc["overview"]:
                over = locator(browser, loc["overview"], f"{base}?part=overview&bounds={fmt(mark)}&centre={centre}{v}", "overview.jpg")
                if over:
                    state["marker"] = over.get("marker")
        finally:
            browser.close()
    return state


def _typst(root: str, out: str, ppi: int | None = None) -> None:
    cmd = [settings.TYPST_BIN, "compile", "--root", root, "--font-path", str(TEMPLATE_DIR / "fonts"),
           "--ignore-system-fonts", os.path.join(root, "page1.typ"), out]
    if ppi:
        cmd += ["--format", "png", "--ppi", str(ppi)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Typst: {(p.stderr or p.stdout).strip()[-2000:]}")


def _basemap_attribution(view: dict) -> str:
    from .api import basemaps

    bm = next((b for b in basemaps() if b["id"] == view.get("basemap")), None)
    return bm["attribution"] if bm else ""


def _compose(product: Product, snapshot: dict, version_n: int | None, draft: bool, tmp: str) -> None:
    sp = snapshot.get("product", {})
    view = sp.get("view") or product.view
    f = page1.frames(sp.get("page_size") or product.page_size, sp.get("locators") or product.locators)
    with ThreadPoolExecutor(max_workers=1) as pool:
        state = pool.submit(_render_maps, str(product.id), version_n, f, DRAFT_DPI if draft else PRINT_DPI, tmp).result()
    data = page1.build(product, snapshot, state, timezone.localtime(), draft, _basemap_attribution(view))
    data["has_inset"] = bool(f["locators"]["area"]) and os.path.exists(os.path.join(tmp, "inset.jpg"))
    data["has_overview"] = bool(f["locators"]["overview"]) and os.path.exists(os.path.join(tmp, "overview.jpg"))
    root = Path(tmp)
    page1.write_assets(root, data)
    shutil.copy(TEMPLATE_DIR / "page1.typ", root / "page1.typ")


def render(version: ProductVersion) -> None:
    product = version.product
    with tempfile.TemporaryDirectory() as tmp:
        _compose(product, version.snapshot, version.n, False, tmp)
        out = os.path.join(tmp, "product.pdf")
        _typst(tmp, out)
        code = (product.code or "RISA").replace(" ", "_")
        name = f"{code}_{product.site.slug}_v{version.n:02d}_{timezone.now():%Y%m%d}.pdf"
        version.pdf_key = storage.save(f"products/{product.id}/{name}", out, content_type="application/pdf")
        # Keep the data the page was made from, for audit and reprints
        version.snapshot = {**version.snapshot, "page": json.loads((Path(tmp) / "data.json").read_text())}
    version.status = "ready"
    version.error = ""
    version.save(update_fields=["pdf_key", "status", "error", "snapshot"])


def render_preview(product: Product) -> None:
    """The current, unsaved-as-a-version product at low resolution, as a PNG."""
    layer_ids = [lyr["id"] for lyr in product.view.get("layers", []) if lyr.get("visible", True)] or None
    snapshot = {"product": {"view": product.view, "page_size": product.page_size, "glance": product.glance,
                            "locators": page1.locators(product.locators)},
                "summary": site_summary(product.site, layer_ids)}
    snapshot = json.loads(json.dumps(snapshot, default=str))
    with tempfile.TemporaryDirectory() as tmp:
        _compose(product, snapshot, None, True, tmp)
        out = os.path.join(tmp, "preview.png")
        _typst(tmp, out, ppi=72)
        product.preview_key = storage.save(f"products/{product.id}/preview.png", out, content_type="image/png")
    product.preview_status = "ready"
    product.preview_error = ""
    product.preview_at = timezone.now()
    product.save(update_fields=["preview_key", "preview_status", "preview_error", "preview_at"])
