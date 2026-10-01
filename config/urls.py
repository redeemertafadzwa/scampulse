from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "ScamPulse Moderation"
admin.site.site_title = "ScamPulse"
admin.site.index_title = "Reports & scam families"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
]
