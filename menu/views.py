from django.db.models import Prefetch
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from comptes.permissions import EstPersonnel
from restaurants.utils import get_restaurant_actif

from .models import Categorie, Plat
from .serializers import CategorieMenuSerializer, PlatSerializer


def est_personnel(user):
    return user.is_authenticated and user.est_personnel


class MenuView(generics.ListAPIView):
    """GET /api/menu/ : le menu public, rangé par catégories."""

    serializer_class = CategorieMenuSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        plats_visibles = Plat.objects.filter(est_actif=True).prefetch_related(
            "groupes_options__options"
        )
        return (
            Categorie.objects.filter(
                restaurant=get_restaurant_actif(),
                est_active=True,
                plats__est_actif=True,
            )
            .distinct()
            .prefetch_related(
                Prefetch("plats", queryset=plats_visibles, to_attr="plats_visibles")
            )
        )


class PlatViewSet(viewsets.ModelViewSet):
    """Les plats : lecture publique, gestion réservée au personnel."""

    serializer_class = PlatSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [EstPersonnel()]

    def get_queryset(self):
        plats = (
            Plat.objects.filter(restaurant=get_restaurant_actif())
            .select_related("categorie")
            .prefetch_related("groupes_options__options")
        )
        if not est_personnel(self.request.user):
            plats = plats.filter(est_actif=True)

        categorie = self.request.query_params.get("categorie")
        if categorie:
            plats = plats.filter(categorie_id=categorie)
        return plats

    def perform_create(self, serializer):
        serializer.save(restaurant=get_restaurant_actif())

    @action(detail=True, methods=["post"], url_path="basculer-disponibilite")
    def basculer_disponibilite(self, request, pk=None):
        """POST /api/menu/plats/<id>/basculer-disponibilite/ : épuisé ↔ disponible."""
        plat = self.get_object()
        plat.est_disponible = not plat.est_disponible
        plat.save(update_fields=["est_disponible", "date_modification"])
        return Response(self.get_serializer(plat).data)