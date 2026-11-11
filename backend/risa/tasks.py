"""Background jobs, on a Postgres-backed queue (Procrastinate): no Redis to run."""

import logging
import os
import tempfile
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from procrastinate.contrib.django import app

from . import analysis, bundles, ingest, kobo, learning, printing, storage
from .models import Detector, KoboSource, Layer, Product, ProductVersion, Response, Transfer, Upload

log = logging.getLogger(__name__)


@app.task(queue="ingest")
def process_upload(upload_id: str, layer_id: str):
    upload = Upload.objects.get(id=upload_id)
    layer = Layer.objects.get(id=layer_id)
    try:
        ingest.process_upload(upload, layer)
    except Exception as e:
        log.exception("Upload %s failed", upload_id)
        layer.status, layer.error = "failed", str(e)[:4000]
        layer.save(update_fields=["status", "error", "updated_at"])


@app.task(queue="kobo")
def sync_kobo(source_id: int, full: bool = False):
    source = KoboSource.objects.select_related("layer").get(id=source_id)
    layer = source.layer
    try:
        n = kobo.sync(source, full=full)
        log.info("Kobo %s: %d submissions written", source.asset_uid, n)
        layer.status, layer.error = "ready", ""
    except Exception as e:
        log.exception("Kobo sync %s failed", source_id)
        source.last_error = str(e)[:2000]
        source.save(update_fields=["last_error"])
        layer.status = "ready" if layer.features.exists() else "failed"
        layer.error = str(e)[:2000]
    layer.save(update_fields=["status", "error", "updated_at"])


@app.periodic(cron="*/5 * * * *")
@app.task(queue="kobo", queueing_lock="sync_all_kobo")
def sync_all_kobo(timestamp: int):
    due = timezone.now() - timedelta(minutes=settings.KOBO_SYNC_MINUTES)
    for s in KoboSource.objects.filter(auto_sync=True).exclude(last_synced_at__gt=due):
        sync_kobo.defer(source_id=s.id)


@app.task(queue="print")
def render_product(version_id: int):
    v = ProductVersion.objects.select_related("product").get(id=version_id)
    try:
        printing.render(v)
    except Exception as e:
        log.exception("Render %s failed", version_id)
        v.status, v.error = "failed", str(e)[:4000]
        v.save(update_fields=["status", "error"])




@app.task(queue="print")
def render_preview(product_id: str):
    p = Product.objects.select_related("site__response").get(id=product_id)
    try:
        printing.render_preview(p)
    except Exception as e:
        log.exception("Preview %s failed", product_id)
        p.preview_status, p.preview_error = "failed", str(e)[:4000]
        p.save(update_fields=["preview_status", "preview_error"])


@app.task(queue="analysis")
def analyse_imagery(layer_id: str):
    layer = Layer.objects.get(id=layer_id)
    try:
        analysis.analyse(layer)
    except Exception as e:
        log.exception("Analysis %s failed", layer_id)
        layer.status, layer.error = "failed", str(e)[:4000]
        layer.save(update_fields=["status", "error", "updated_at"])


@app.task(queue="analysis")
def train_detector(detector_id: int):
    d = Detector.objects.select_related("response").get(id=detector_id)
    try:
        learning.train(d)
    except Exception as e:
        log.exception("Training %s failed", detector_id)
        d.status, d.error = "failed", str(e)[:2000]
        d.save(update_fields=["status", "error"])


@app.task(queue="ingest")
def export_bundle(transfer_id: str):
    t = Transfer.objects.select_related("response").get(id=transfer_id)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, f"{t.response.slug}.risa.zip")
            bundles.export_bundle(t.response, path, imagery=t.options.get("imagery", True),
                                  originals=t.options.get("originals", False))
            t.size = os.path.getsize(path)
            t.file_key = storage.save(f"bundles/{t.id}/{os.path.basename(path)}", path, content_type="application/zip")
        t.status = "ready"
    except Exception as e:
        log.exception("Bundle export %s failed", transfer_id)
        t.status, t.error = "failed", str(e)[:4000]
    t.save()


@app.task(queue="ingest")
def import_bundle(transfer_id: str, upload_id: str):
    t = Transfer.objects.get(id=transfer_id)
    upload = Upload.objects.get(id=upload_id)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bundle.zip")
            storage.concat_parts([upload.part_key(n) for n in range(upload.part_count)], path)
            t.result = bundles.import_bundle(path, edit_key_hash=upload.layer_options.get("edit_key_hash"))
        t.response_id = Response.objects.get(slug=t.result["response"]).id
        t.status = "ready"
    except bundles.BundleError as e:
        t.status, t.error = "failed", str(e)
    except Exception as e:
        log.exception("Bundle import %s failed", transfer_id)
        t.status, t.error = "failed", str(e)[:4000]
    t.save()
    storage.delete_prefix(f"uploads/{upload.id}")
    upload.delete()


@app.periodic(cron="17 3 * * *")
@app.task(queue="ingest", queueing_lock="clean_bundles")
def clean_bundles(timestamp: int):
    """Exported bundles can be gigabytes: keep them a week, then make them again if needed."""
    old = timezone.now() - timedelta(days=settings.BUNDLE_KEEP_DAYS)
    for t in Transfer.objects.filter(created_at__lt=old):
        storage.delete_prefix(f"bundles/{t.id}")
        t.delete()
    for u in Upload.objects.filter(kind="bundle", created_at__lt=old):
        storage.delete_prefix(f"uploads/{u.id}")
        u.delete()
