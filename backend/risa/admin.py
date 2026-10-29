from django.contrib.gis import admin

from .models import Feature, KoboSource, Layer, Product, ProductVersion, Response, Site


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "country", "glide", "private", "created_at")
    exclude = ("edit_key_hash",)
    actions = ["rotate_key"]

    @admin.action(description="Rotate the edit key (shown once)")
    def rotate_key(self, request, queryset):
        for r in queryset:
            key = r.set_edit_key()
            r.save(update_fields=["edit_key_hash"])
            self.message_user(request, f"{r.slug}: new edit key {key}")


@admin.register(Site)
class SiteAdmin(admin.GISModelAdmin):
    list_display = ("name", "response", "kind")
    list_filter = ("response",)


@admin.register(Layer)
class LayerAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "kind", "status", "z_order")
    list_filter = ("kind", "status")


@admin.register(Feature)
class FeatureAdmin(admin.GISModelAdmin):
    list_display = ("label", "layer", "risa_type", "risa_status")
    list_filter = ("risa_type", "risa_status")


@admin.register(KoboSource)
class KoboSourceAdmin(admin.ModelAdmin):
    list_display = ("asset_name", "server_url", "asset_uid", "last_synced_at", "submission_count")
    exclude = ("token_encrypted",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "site", "updated_at")


@admin.register(ProductVersion)
class ProductVersionAdmin(admin.ModelAdmin):
    list_display = ("product", "n", "status", "rendered_at")
