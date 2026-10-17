from rest_framework.exceptions import NotFound

from .models import Restaurant


def get_restaurant_actif():
    """Renvoie le restaurant actif, ou répond 404 s'il n'y en a pas."""
    restaurant = Restaurant.objects.filter(est_actif=True).first()
    if restaurant is None:
        raise NotFound("Aucun restaurant n'est encore configuré.")
    return restaurant