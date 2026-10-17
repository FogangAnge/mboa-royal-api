from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import VilleListView, ZoneLivraisonViewSet

router = DefaultRouter()
router.register("livraison", ZoneLivraisonViewSet, basename="zone-livraison")

urlpatterns = [
    path("villes/", VilleListView.as_view(), name="villes"),
    *router.urls,
]