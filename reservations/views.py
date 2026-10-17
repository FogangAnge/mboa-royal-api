from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from commandes.whatsapp import numero_international
from menu.models import JOURS
from restaurants.utils import get_restaurant_actif

from .models import Reservation, TransitionInvalide
from .serializers import (
    ChangementStatutReservationSerializer,
    DisponibiliteSerializer,
    ReservationCreationSerializer,
    ReservationSerializer,
)
from .services import places_restantes


def lien_whatsapp_reservation(reservation):
    from urllib.parse import quote

    moment = timezone.localtime(reservation.date_heure)
    message = "\n".join([
        f"Bonjour {reservation.restaurant.nom}, je souhaite réserver une table :",
        "",
        f"N° {reservation.numero}",
        f"Le {JOURS[moment.weekday()]} {moment:%d/%m/%Y à %H:%M}",
        f"Pour {reservation.nb_personnes} personne(s)",
        f"Nom : {reservation.nom} — Tél : {reservation.telephone}",
        "",
        "Merci de confirmer ma réservation.",
    ])
    numero = numero_international(reservation.restaurant.whatsapp)
    return f"https://wa.me/{numero}?text={quote(message)}"


class ReservationViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET  /api/reservations/disponibilite/   reste-t-il de la place ? (public)
    POST /api/reservations/                 demander une réservation (public)
    GET  /api/reservations/                 toutes (personnel) ou les miennes (client)
    GET  /api/reservations/<numero>/        détail
    POST /api/reservations/<numero>/statut/ confirmer, refuser, annuler, venu, absent
    """

    lookup_field = "numero"

    def get_permissions(self):
        if self.action in ("create", "disponibilite"):
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_throttles(self):
        if self.action == "create":
            self.throttle_scope = "reservation"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def get_serializer_class(self):
        if self.action == "create":
            return ReservationCreationSerializer
        return ReservationSerializer

    def get_queryset(self):
        reservations = Reservation.objects.filter(
            restaurant=get_restaurant_actif()
        ).select_related("restaurant")
        user = self.request.user
        if not user.est_personnel:
            return reservations.filter(client=user)

        statut = self.request.query_params.get("statut")
        if statut:
            reservations = reservations.filter(statut=statut)
        jour = self.request.query_params.get("date")
        if jour:
            try:
                date = parse_date(jour)
            except ValueError:
                date = None
            if date is None:
                raise ValidationError({"date": "Date invalide. Format attendu : AAAA-MM-JJ."})
            reservations = reservations.filter(date_heure__date=date)
        return reservations

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = serializer.save()
        reponse = ReservationSerializer(reservation, context=self.get_serializer_context()).data
        reponse["lien_whatsapp"] = lien_whatsapp_reservation(reservation)
        return Response(reponse, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], authentication_classes=[])
    def disponibilite(self, request):
        """GET /api/reservations/disponibilite/?date_heure=...&nb_personnes=4"""
        entree = DisponibiliteSerializer(data=request.query_params)
        entree.is_valid(raise_exception=True)
        restaurant = get_restaurant_actif()
        moment = entree.validated_data["date_heure"]
        nb = entree.validated_data["nb_personnes"]

        ouvert = restaurant.est_ouvert(moment)
        restantes = places_restantes(restaurant, moment) if ouvert else 0
        return Response({
            "date_heure": moment,
            "ouvert": ouvert,
            "places_restantes": restantes,
            "disponible": ouvert and nb <= restantes,
        })

    @action(detail=True, methods=["post"])
    def statut(self, request, numero=None):
        """POST /api/reservations/<numero>/statut/"""
        entree = ChangementStatutReservationSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        nouveau = entree.validated_data["statut"]
        reservation = self.get_object()

        if not request.user.est_personnel:
            if nouveau != Reservation.Statut.ANNULEE:
                raise PermissionDenied("Vous pouvez seulement annuler votre réservation.")
            if reservation.date_heure <= timezone.now():
                raise PermissionDenied("L'heure de cette réservation est déjà passée.")

        erreur = None
        with transaction.atomic():
            reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
            try:
                reservation.changer_statut(
                    nouveau,
                    auteur=request.user,
                    commentaire=entree.validated_data.get("commentaire", ""),
                )
            except TransitionInvalide as exc:
                erreur = str(exc)
        if erreur:
            raise ValidationError({"detail": erreur})
        return Response(ReservationSerializer(reservation, context=self.get_serializer_context()).data)