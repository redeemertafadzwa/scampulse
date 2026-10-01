from django.urls import path

from . import views

urlpatterns = [
    path("", views.app, name="app"),
    path("privacy/", views.privacy, name="privacy"),
    path("moderate/", views.moderate, name="moderate"),
    path("moderate/<int:family_id>/<str:action>/", views.moderate_action, name="moderate_action"),
    path("health", views.health, name="health"),
    path("sw.js", views.service_worker, name="sw"),
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("api/reports/", views.reports, name="reports"),
    path("api/vote/", views.vote, name="vote"),
    path("api/feed/", views.feed, name="feed"),
    path("api/blocklist/", views.blocklist, name="blocklist"),
    path("api/model-version/", views.model_version, name="model_version"),
]
