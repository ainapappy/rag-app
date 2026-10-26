"""Routes du chatbot (≈ routes/web.php, les name= sont les noms de routes)."""

from django.urls import path

from chatbot import views

urlpatterns = [
    path("accounts/login/", views.login_view, name="login"),
    path("accounts/logout/", views.logout_view, name="logout"),
    path("", views.ChatView.as_view(), name="chat"),
    path("chat/new/", views.ConversationCreateView.as_view(), name="chat_new"),
    path("chat/<int:pk>/", views.ConversationDetailView.as_view(), name="chat_detail"),
    path("chat/<int:pk>/delete/", views.ConversationDeleteView.as_view(), name="chat_delete"),
    path("chat/<int:pk>/send/", views.SendView.as_view(), name="chat_send"),
]
