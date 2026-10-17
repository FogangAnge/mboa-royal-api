from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import CommandeViewSet, SuiviCommandeView

router = SimpleRouter()
router.register("", CommandeViewSet, basename="commande")

urlpatterns = [
    path("suivi/", SuiviCommandeView.as_view(), name="suivi-commande"),
    *router.urls,
]