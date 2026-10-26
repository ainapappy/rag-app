"""URLs racine du projet : admin, API JSON et application chatbot."""

from django.contrib import admin
from django.urls import include, path

from chatbot.api import api as ninja_api

api_patterns = [
    path("", ninja_api.urls),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(api_patterns)),
    path("", include("chatbot.urls")),
]
