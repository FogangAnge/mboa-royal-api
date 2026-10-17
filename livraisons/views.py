from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from comptes.models import Utilisateur
from comptes.permissions import EstLivreur, EstPersonnel
from restaurants.utils import get_restaurant_actif

from .models import VersementLivreur
from .serializers import VersementSerializer
from .services import bilan_livreur, courses_du_jour


def lire_jour(request):
    """Lit ?date=AAAA-MM-JJ, ou renvoie aujourd'hui."""
    valeur = request.query_params.get("date")
    if not valeur:
        return timezone.localdate()
    try:
        jour = parse_date(valeur)
    except ValueError:
        jour = None
    if jour is None:
        raise ValidationError({"date": "Date invalide. Format attendu : AAAA-MM-JJ."})
    return jour


class CaisseView(APIView):
    """GET /api/livraisons/caisse/?date=2026-10-17 : le bilan de tous les livreurs."""

    permission_classes = [EstPersonnel]

    def get(self, request):
        restaurant = get_restaurant_actif()
        jour = lire_jour(request)
        livreurs = Utilisateur.objects.filter(
            role=Utilisateur.Role.LIVREUR, is_active=True
        ).order_by("nom")
        bilans = [bilan_livreur(restaurant, livreur, jour) for livreur in livreurs]
        return Response({
            "date": jour,
            "livreurs": bilans,
            "total_encaisse": sum(b["encaisse"] for b in bilans),
            "total_reste_a_verser": sum(b["reste_a_verser"] for b in bilans),
        })


class MaCaisseView(APIView):
    """GET /api/livraisons/caisse/moi/ : le bilan et les courses du livreur connecté."""

    permission_classes = [EstLivreur]

    def get(self, request):
        restaurant = get_restaurant_actif()
        jour = lire_jour(request)
        courses = courses_du_jour(restaurant, request.user, jour)
        return Response({
            "date": jour,
            **bilan_livreur(restaurant, request.user, jour),
            "courses": [
                {
                    "numero": c.numero,
                    "quartier": c.quartier,
                    "total": c.total,
                    "montant_encaisse": c.montant_encaisse,
                    "mode_paiement": c.get_mode_paiement_display(),
                }
                for c in courses
            ],
        })


class DisponibiliteView(APIView):
    """POST /api/livraisons/disponibilite/ : le livreur bascule disponible ↔ indisponible."""

    permission_classes = [EstLivreur]

    def post(self, request):
        user = request.user
        user.disponible = not user.disponible
        user.save(update_fields=["disponible"])
        return Response({"disponible": user.disponible})


class VersementViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """GET / POST /api/livraisons/versements/ : les versements des livreurs."""

    serializer_class = VersementSerializer
    permission_classes = [EstPersonnel]

    def get_queryset(self):
        versements = VersementLivreur.objects.filter(
            restaurant=get_restaurant_actif()
        ).select_related("livreur", "recu_par")
        if self.request.query_params.get("date"):
            versements = versements.filter(jour=lire_jour(self.request))
        return versements

    def perform_create(self, serializer):
        serializer.save(restaurant=get_restaurant_actif(), recu_par=self.request.user)