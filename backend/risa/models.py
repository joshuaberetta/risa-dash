import hashlib
import secrets
import uuid

from django.contrib.gis.db import models

STATUS_CHOICES = [("ok", "Working"), ("partial", "Partly"), ("no", "Not working"), ("unknown", "Not assessed")]


def new_edit_key() -> str:
    return secrets.token_urlsafe(18)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


class Response(models.Model):
    """One emergency response, e.g. the June 2026 earthquake in Venezuela."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=200)
    hazard = models.CharField(max_length=60, blank=True)
    country = models.CharField(max_length=3, blank=True, help_text="ISO 3166-1 alpha-3")
    glide = models.CharField(max_length=40, blank=True)
    start_date = models.DateField(null=True, blank=True)
    language = models.CharField(max_length=8, default="en")
    edit_key_hash = models.CharField(max_length=64)
    private = models.BooleanField(default=False, help_text="Hidden from the index page")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def set_edit_key(self, key: str | None = None) -> str:
        key = key or new_edit_key()
        self.edit_key_hash = hash_key(key)
        return key

    def check_edit_key(self, key: str | None) -> bool:
        return bool(key) and secrets.compare_digest(self.edit_key_hash, hash_key(key))


class Site(models.Model):
    """A camp, collective centre or settlement assessed in a response."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    response = models.ForeignKey(Response, on_delete=models.CASCADE, related_name="sites")
    slug = models.SlugField(max_length=80)
    name = models.CharField(max_length=200)
    place = models.CharField(max_length=200, blank=True, help_text="Locality, district, country")
    kind = models.CharField(max_length=40, default="camp")
    boundary = models.MultiPolygonField(srid=4326, null=True, blank=True)
    # {center: [lon, lat], zoom, bearing}
    default_view = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["response", "slug"], name="site_slug_per_response")]

    def __str__(self):
        return f"{self.response.slug}/{self.slug}"


class Layer(models.Model):
    KINDS = [
        ("raster", "Raster (COG)"),
        ("vector", "Vector"),
        ("kobo", "Kobo"),
        ("annotations", "Annotations"),
        ("xyz", "XYZ tiles"),
        ("wms", "WMS"),
        ("cog_url", "COG by URL"),
    ]
    STATUSES = [("processing", "Processing"), ("ready", "Ready"), ("failed", "Failed")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="layers")
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=20, choices=KINDS)
    status = models.CharField(max_length=20, choices=STATUSES, default="ready")
    error = models.TextField(blank=True)
    # Storage key (raster) or URL (xyz, wms, cog_url)
    source = models.CharField(max_length=1000, blank=True)
    # Original upload, kept for re-processing and download
    original = models.CharField(max_length=1000, blank=True)
    # {preset, color, opacity, label_field, ...}
    style = models.JSONField(default=dict, blank=True)
    z_order = models.IntegerField(default=0)
    visible_default = models.BooleanField(default=True)
    attribution = models.CharField(max_length=500, blank=True)
    licence = models.CharField(max_length=100, blank=True)
    captured_at = models.DateField(null=True, blank=True)
    resolution_cm = models.FloatField(null=True, blank=True)
    bbox = models.JSONField(null=True, blank=True)  # [w, s, e, n]
    online_only = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-z_order", "created_at"]

    def __str__(self):
        return self.name

    @property
    def is_vector(self):
        return self.kind in {"vector", "kobo", "annotations"}


class Feature(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE, related_name="features")
    geom = models.GeometryField(srid=4326)
    properties = models.JSONField(default=dict, blank=True)
    risa_type = models.CharField(max_length=40, blank=True)
    risa_status = models.CharField(max_length=10, choices=STATUS_CHOICES, blank=True)
    label = models.CharField(max_length=200, blank=True)
    # Kobo _uuid or source feature id: upserts on re-sync
    source_ref = models.CharField(max_length=200, blank=True, db_index=True)
    observed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["layer", "risa_type", "risa_status"])]


class KoboSource(models.Model):
    layer = models.OneToOneField(Layer, on_delete=models.CASCADE, related_name="kobo")
    server_url = models.URLField()
    asset_uid = models.CharField(max_length=64)
    asset_name = models.CharField(max_length=300, blank=True)
    token_encrypted = models.TextField()
    # {geo, type, status, label, popup: [...], sensitive: [...], type_map: {}, status_map: {}}
    field_map = models.JSONField(default=dict, blank=True)
    auto_sync = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_submission_id = models.BigIntegerField(default=0)
    last_error = models.TextField(blank=True)
    submission_count = models.IntegerField(default=0)


class Upload(models.Model):
    """A chunked, resumable upload. Parts live in storage under uploads/<id>/."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="uploads")
    filename = models.CharField(max_length=300)
    size = models.BigIntegerField()
    chunk_size = models.IntegerField()
    kind = models.CharField(max_length=20)  # raster | vector
    layer_name = models.CharField(max_length=200)
    layer_options = models.JSONField(default=dict, blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def part_count(self) -> int:
        return max(1, -(-self.size // self.chunk_size))

    def part_key(self, n: int) -> str:
        return f"uploads/{self.id}/{n:05d}"


class Product(models.Model):
    PAGE_SIZES = [("A3", "A3"), ("A4", "A4")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="products")
    kind = models.CharField(max_length=20, default="page1")
    title = models.CharField(max_length=200, default="Common Operational Picture")
    code = models.CharField(max_length=40, blank=True, help_text="Map code, e.g. MA023")
    version_label = models.CharField(max_length=200, default="Initial assessment · v1.0")
    page_size = models.CharField(max_length=4, choices=PAGE_SIZES, default="A3")
    # {center, zoom, bearing, basemap, layers: [{id, visible, opacity}]}
    view = models.JSONField(default=dict)
    key_message = models.TextField(blank=True)
    # [{value, label, tbc}] overrides for the four at-a-glance figures; empty = computed
    glance = models.JSONField(default=list, blank=True)
    authority = models.CharField(max_length=200, blank=True, help_text="Leading national authority")
    sources = models.TextField(blank=True, help_text="Blank: built from the layers' attributions")
    disclaimer = models.TextField(
        default="The boundaries and names shown on this map do not imply official endorsement or acceptance."
    )
    credits = models.CharField(max_length=300, default="HI/Atlas Logistique · MapAction · Kobo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class ProductVersion(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="versions")
    n = models.IntegerField()
    status = models.CharField(max_length=20, default="processing")
    error = models.TextField(blank=True)
    pdf_key = models.CharField(max_length=500, blank=True)
    # The product and its data as printed, so a reprint matches the original
    snapshot = models.JSONField(default=dict)
    rendered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-n"]
        constraints = [models.UniqueConstraint(fields=["product", "n"], name="version_per_product")]


class Logo(models.Model):
    """Logos for the header band and footer (national authority, partners)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    response = models.ForeignKey(Response, on_delete=models.CASCADE, related_name="logos")
    name = models.CharField(max_length=200)
    key = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
