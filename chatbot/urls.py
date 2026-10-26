"""Routes du chatbot (≈ routes/web.php, les name= sont les noms de routes)."""

from django.urls import path
from django.views.generic import RedirectView

from chatbot import views

urlpatterns = [
    path("accounts/login/", views.login_view, name="login"),
    path("accounts/logout/", views.logout_view, name="logout"),
    path("health/", views.HealthView.as_view(), name="health"),
    path("chat/", views.ChatView.as_view(), name="chat"),
    path("", RedirectView.as_view(pattern_name="chat"), name="home"),
    path("chat/new/", views.ConversationCreateView.as_view(), name="chat_new"),
    path("chat/<int:pk>/", views.ConversationDetailView.as_view(), name="chat_detail"),
    path("chat/<int:pk>/delete/", views.ConversationDeleteView.as_view(), name="chat_delete"),
    path("chat/<int:pk>/send/", views.SendView.as_view(), name="chat_send"),
]
