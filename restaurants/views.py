from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.permissions import SAFE_METHODS, AllowAny

from comptes.permissions import EstProprietaire

from .models import Restaurant
from .serializers import RestaurantSerializer


class RestaurantView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/restaurant/ : informations publiques du restaurant.
    PATCH /api/restaurant/ : modification, réservée au propriétaire.
    """

    serializer_class = RestaurantSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [EstProprietaire()]

    def get_object(self):
        restaurant = (
            Restaurant.objects.filter(est_actif=True).prefetch_related("horaires").first()
        )
        if restaurant is None:
            raise NotFound("Aucun restaurant n'est encore configuré.")
        self.check_object_permissions(self.request, restaurant)
        return restaurant