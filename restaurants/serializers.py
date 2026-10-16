from rest_framework import serializers

from comptes.serializers import normaliser_telephone

from .models import HoraireOuverture, Restaurant


class HoraireOuvertureSerializer(serializers.ModelSerializer):
    jour_libelle = serializers.CharField(source="get_jour_display", read_only=True)

    class Meta:
        model = HoraireOuverture
        fields = ("jour", "jour_libelle", "ferme", "ouverture", "fermeture")


class RestaurantSerializer(serializers.ModelSerializer):
    horaires = HoraireOuvertureSerializer(many=True, read_only=True)
    est_ouvert = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = (
            "id", "nom", "slogan", "description", "logo",
            "pays", "ville", "quartier", "adresse", "latitude", "longitude",
            "telephone", "whatsapp", "email",
            "couleur_principale", "couleur_accent",
            "capacite_salle", "delai_preparation_min", "devise",
            "horaires", "est_ouvert",
        )
        read_only_fields = ("id",)

    def get_est_ouvert(self, obj):
        return obj.est_ouvert()

    def validate_telephone(self, valeur):
        return normaliser_telephone(valeur)

    def validate_whatsapp(self, valeur):
        return normaliser_telephone(valeur)