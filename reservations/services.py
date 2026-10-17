from datetime import timedelta

from django.db.models import Sum

from .models import Reservation

DUREE_RESERVATION = timedelta(hours=2)
STATUTS_OCCUPANTS = (Reservation.Statut.EN_ATTENTE, Reservation.Statut.CONFIRMEE)


def places_occupees(restaurant, moment):
    """Personnes déjà attendues dans une fenêtre de ± 2 heures autour du moment demandé."""
    total = Reservation.objects.filter(
        restaurant=restaurant,
        statut__in=STATUTS_OCCUPANTS,
        date_heure__gt=moment - DUREE_RESERVATION,
        date_heure__lt=moment + DUREE_RESERVATION,
    ).aggregate(total=Sum("nb_personnes"))["total"]
    return total or 0


def places_restantes(restaurant, moment):
    return max(restaurant.capacite_salle - places_occupees(restaurant, moment), 0)