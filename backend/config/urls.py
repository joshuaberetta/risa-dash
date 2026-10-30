from django.contrib import admin
from django.urls import path, re_path

from risa.api import api
from risa.views import guide, media, spa

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    re_path(r"^media/(?P<key>.+)$", media, name="media"),
    re_path(r"^guide/?$", guide),
    # Everything else is the React app
    re_path(r"^(?!api/|admin/|static/|media/).*$", spa),
]
