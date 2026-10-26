"""Routes du chatbot (≈ routes/web.php, les name= sont les noms de routes)."""

from django.urls import path
from django.views.generic import RedirectView

from chatbot import api_views, views

urlpatterns = [
    path("accounts/login/", views.login_view, name="login"),
    path("accounts/logout/", views.logout_view, name="logout"),
    path("health/", views.HealthView.as_view(), name="health"),
    path("chat/", views.ChatView.as_view(), name="chat"),
    path("", RedirectView.as_view(pattern_name="chat"), name="home"),
    path("chat/<int:pk>/", views.ConversationDetailView.as_view(), name="chat_detail"),
    path("chat/<int:pk>/send/", views.SendView.as_view(), name="chat_send"),
    # Endpoints JSON de l'interface Vue (session + CSRF, ≠ API publique à clés).
    path(
        "chat/api/conversations/",
        api_views.ConversationListApiView.as_view(),
        name="chat_api_conversations",
    ),
    path(
        "chat/api/conversations/<int:pk>/",
        api_views.ConversationDetailApiView.as_view(),
        name="chat_api_conversation_detail",
    ),
    path("chat/api/me/", api_views.MeApiView.as_view(), name="api_me"),
    path("accounts/api/login/", api_views.LoginApiView.as_view(), name="api_login"),
    path("accounts/api/logout/", api_views.LogoutApiView.as_view(), name="api_logout"),
]
