from rest_framework import mixins, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from restaurants.utils import get_restaurant_actif

from .models import Commande
from .serializers import CommandeCreationSerializer, CommandeSerializer
from .whatsapp import lien_whatsapp


class CommandeViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    POST /api/commandes/            passer une commande (avec ou sans compte)
    GET  /api/commandes/            mes commandes / toutes / mes courses, selon le rôle
    GET  /api/commandes/<numero>/   détail
    """

    lookup_field = "numero"

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return CommandeCreationSerializer
        return CommandeSerializer

    def get_queryset(self):
        commandes = (
            Commande.objects.filter(restaurant=get_restaurant_actif())
            .select_related("restaurant", "livreur", "client")
            .prefetch_related("lignes", "historique")
        )
        user = self.request.user
        if user.est_personnel:
            statut = self.request.query_params.get("statut")
            return commandes.filter(statut=statut) if statut else commandes
        if user.est_livreur:
            return commandes.filter(livreur=user)
        return commandes.filter(client=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        commande = serializer.save()

        reponse = CommandeSerializer(commande, context=self.get_serializer_context()).data
        reponse["code_livraison"] = commande.code_livraison
        reponse["lien_whatsapp"] = lien_whatsapp(commande)
        return Response(reponse, status=status.HTTP_201_CREATED)