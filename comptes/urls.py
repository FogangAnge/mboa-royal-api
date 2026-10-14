from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import InscriptionView, MoiView

urlpatterns = [
    path("inscription/", InscriptionView.as_view(), name="inscription"),
    path("connexion/", TokenObtainPairView.as_view(), name="connexion"),
    path("token/rafraichir/", TokenRefreshView.as_view(), name="token-rafraichir"),
    path("moi/", MoiView.as_view(), name="moi"),
]

