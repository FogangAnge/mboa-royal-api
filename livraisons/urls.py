from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import CaisseView, DisponibiliteView, MaCaisseView, VersementViewSet

router = SimpleRouter()
router.register("versements", VersementViewSet, basename="versement")

urlpatterns = [
    path("caisse/", CaisseView.as_view(), name="caisse"),
    path("caisse/moi/", MaCaisseView.as_view(), name="ma-caisse"),
    path("disponibilite/", DisponibiliteView.as_view(), name="disponibilite"),
    *router.urls,
]