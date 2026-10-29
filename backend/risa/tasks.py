"""Background jobs, on a Postgres-backed queue (Procrastinate): no Redis to run."""

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from procrastinate.contrib.django import app

from . import analysis, ingest, kobo, learning, printing
from .models import Detector, KoboSource, Layer, Product, ProductVersion, Upload

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
