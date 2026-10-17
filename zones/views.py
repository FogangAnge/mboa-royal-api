from rest_framework import generics, viewsets
from rest_framework.permissions import AllowAny

from comptes.permissions import EstPersonnel
from restaurants.utils import get_restaurant_actif

from .models import Ville, ZoneLivraison
from .serializers import VilleSerializer, ZoneLivraisonSerializer


class VilleListView(generics.ListAPIView):
    """GET /api/zones/villes/ : les villes où le restaurant livre."""

    serializer_class = VilleSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return (
            Ville.objects.filter(
                quartiers__zones_livraison__restaurant=get_restaurant_actif(),
                quartiers__zones_livraison__est_active=True,
            )
            .select_related("region")
            .distinct()
        )


class ZoneLivraisonViewSet(viewsets.ModelViewSet):
    """
    GET    /api/zones/livraison/           liste (public), filtrable avec ?ville=<id>
    GET    /api/zones/livraison/<id>/      détail (public)
    POST   /api/zones/livraison/           création (personnel)
    PATCH  /api/zones/livraison/<id>/      modification (personnel)
    DELETE /api/zones/livraison/<id>/      suppression (personnel)
    """

    serializer_class = ZoneLivraisonSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [EstPersonnel()]

    def get_queryset(self):
        zones = ZoneLivraison.objects.filter(
            restaurant=get_restaurant_actif()
        ).select_related("quartier__ville")

        user = self.request.user
        if not (user.is_authenticated and user.est_personnel):
            zones = zones.filter(est_active=True)

        ville = self.request.query_params.get("ville")
        if ville:
            zones = zones.filter(quartier__ville_id=ville)
        return zones

    def perform_create(self, serializer):
        serializer.save(restaurant=get_restaurant_actif())