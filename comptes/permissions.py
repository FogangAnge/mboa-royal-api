from rest_framework.permissions import BasePermission

from .models import Utilisateur


class EstProprietaire(BasePermission):
    """Autorise uniquement le propriétaire du restaurant."""

    message = "Cette action est réservée au propriétaire."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.role == Utilisateur.Role.PROPRIETAIRE
        )


class EstPersonnel(BasePermission):
    """Autorise le propriétaire et le gérant."""

    message = "Cette action est réservée au personnel du restaurant."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.est_personnel)


class EstLivreur(BasePermission):
    """Autorise uniquement les livreurs."""

    message = "Cette action est réservée aux livreurs."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.est_livreur)