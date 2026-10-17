from rest_framework import serializers

from restaurants.utils import get_restaurant_actif

from .models import Ville, ZoneLivraison


class VilleSerializer(serializers.ModelSerializer):
    region = serializers.CharField(source="region.nom", read_only=True)

    class Meta:
        model = Ville
        fields = ("id", "nom", "region")


class ZoneLivraisonSerializer(serializers.ModelSerializer):
    quartier_nom = serializers.CharField(source="quartier.nom", read_only=True)
    ville_id = serializers.IntegerField(source="quartier.ville_id", read_only=True)
    ville_nom = serializers.CharField(source="quartier.ville.nom", read_only=True)

    class Meta:
        model = ZoneLivraison
        fields = (
            "id", "quartier", "quartier_nom", "ville_id", "ville_nom",
            "frais", "delai_min", "est_active",
        )

    def validate_quartier(self, quartier):
        existe = ZoneLivraison.objects.filter(
            restaurant=get_restaurant_actif(), quartier=quartier
        )
        if self.instance is not None:
            existe = existe.exclude(pk=self.instance.pk)
        if existe.exists():
            raise serializers.ValidationError("Ce quartier a déjà une zone de livraison.")
        return quartier