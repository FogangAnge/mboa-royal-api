from rest_framework.routers import SimpleRouter

from .views import CommandeViewSet

router = SimpleRouter()
router.register("", CommandeViewSet, basename="commande")

urlpatterns = router.urls