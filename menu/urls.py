from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import MenuView, PlatViewSet

router = SimpleRouter()
router.register("plats", PlatViewSet, basename="plat")

urlpatterns = [
    path("", MenuView.as_view(), name="menu"),
    *router.urls,
]