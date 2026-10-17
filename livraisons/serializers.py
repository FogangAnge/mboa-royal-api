from django.utils import timezone
from rest_framework import serializers

from comptes.models import Utilisateur
from restaurants.utils import get_restaurant_actif

from .models import VersementLivreur
from .services import bilan_livreur


class VersementSerializer(serializers.ModelSerializer):
    livreur = serializers.PrimaryKeyRelatedField(
        queryset=Utilisateur.objects.filter(role=Utilisateur.Role.LIVREUR)
    )
    livreur_nom = serializers.CharField(source="livreur.nom", read_only=True)
    recu_par_nom = serializers.CharField(source="recu_par.nom", read_only=True, default=None)
    montant = serializers.IntegerField(min_value=1)

    class Meta:
        model = VersementLivreur
        fields = ("id", "livreur", "livreur_nom", "montant", "jour", "note", "recu_par_nom", "date_creation")
        read_only_fields = ("id", "date_creation")

    def validate(self, data):
        jour = data.get("jour") or timezone.localdate()
        bilan = bilan_livreur(get_restaurant_actif(), data["livreur"], jour)
        if data["montant"] > bilan["reste_a_verser"]:
            raise serializers.ValidationError({
                "montant": f"Pour le {jour:%d/%m/%Y}, ce livreur ne doit que "
                           f"{bilan['reste_a_verser']} FCFA."
            })
        return data