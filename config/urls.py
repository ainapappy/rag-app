"""URLs racine du projet : admin + application chatbot (≈ routes/web.php)."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("chatbot.urls")),
]
