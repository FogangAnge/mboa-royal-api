from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from comptes.models import Utilisateur
from comptes.serializers import normaliser_telephone
from restaurants.models import Restaurant
from restaurants.utils import get_restaurant_actif

from .models import Reservation
from .services import places_restantes

DELAI_MINIMUM = timedelta(hours=1)
DELAI_MAXIMUM = timedelta(days=60)
MAX_RESERVATIONS_EN_ATTENTE = 2


def valider_creneau(restaurant, date_heure):
    maintenant = timezone.now()
    if date_heure < maintenant + DELAI_MINIMUM:
        raise serializers.ValidationError(
            {"date_heure": "Réservez au moins une heure à l'avance."}
        )
    if date_heure > maintenant + DELAI_MAXIMUM:
        raise serializers.ValidationError(
            {"date_heure": "On ne peut pas réserver plus de deux mois à l'avance."}
        )
    if not restaurant.est_ouvert(date_heure):
        raise serializers.ValidationError(
            {"date_heure": "Le restaurant est fermé à cette heure-là."}
        )


class DisponibiliteSerializer(serializers.Serializer):
    date_heure = serializers.DateTimeField()
    nb_personnes = serializers.IntegerField(min_value=1, max_value=100)


class ReservationCreationSerializer(serializers.Serializer):
    nom = serializers.CharField(required=False, max_length=150)
    telephone = serializers.CharField(required=False, max_length=20)
    date_heure = serializers.DateTimeField()
    nb_personnes = serializers.IntegerField(min_value=1, max_value=100)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate_telephone(self, valeur):
        return normaliser_telephone(valeur)

    def validate(self, data):
        user = self.context["request"].user
        restaurant = get_restaurant_actif()

        if user.is_authenticated:
            if user.est_bloque:
                raise serializers.ValidationError(
                    "Ce compte ne peut pas réserver. Contactez le restaurant."
                )
            data.setdefault("nom", user.nom or user.telephone)
            data.setdefault("telephone", user.telephone)
        else:
            erreurs = {}
            if not data.get("nom"):
                erreurs["nom"] = "Indiquez votre nom."
            if not data.get("telephone"):
                erreurs["telephone"] = "Indiquez votre numéro de téléphone."
            if erreurs:
                raise serializers.ValidationError(erreurs)

        if Utilisateur.objects.filter(telephone=data["telephone"], est_bloque=True).exists():
            raise serializers.ValidationError("Ce numéro ne peut pas réserver. Contactez le restaurant.")

        en_attente = Reservation.objects.filter(
            restaurant=restaurant,
            telephone=data["telephone"],
            statut=Reservation.Statut.EN_ATTENTE,
            date_heure__gt=timezone.now(),
        ).count()
        if en_attente >= MAX_RESERVATIONS_EN_ATTENTE:
            raise serializers.ValidationError(
                "Vous avez déjà des réservations en attente de confirmation. "
                "Merci d'attendre notre réponse sur WhatsApp."
            )

        valider_creneau(restaurant, data["date_heure"])
        if data["nb_personnes"] > restaurant.capacite_salle:
            raise serializers.ValidationError({
                "nb_personnes": "Pour un groupe de cette taille, contactez-nous directement sur WhatsApp."
            })
        return data

    @transaction.atomic
    def create(self, data):
        # On verrouille le restaurant : deux demandes simultanées sont traitées l'une après l'autre.
        restaurant = Restaurant.objects.select_for_update().get(pk=get_restaurant_actif().pk)
        restantes = places_restantes(restaurant, data["date_heure"])
        if data["nb_personnes"] > restantes:
            message = (
                f"Il ne reste que {restantes} place(s) à cette heure-là."
                if restantes else "Nous sommes complets à cette heure-là. Essayez un autre horaire."
            )
            raise serializers.ValidationError({"nb_personnes": message})

        user = self.context["request"].user
        return Reservation.objects.create(
            restaurant=restaurant,
            client=user if user.is_authenticated else None,
            nom=data["nom"],
            telephone=data["telephone"],
            date_heure=data["date_heure"],
            nb_personnes=data["nb_personnes"],
            note=data.get("note", ""),
        )


class ReservationSerializer(serializers.ModelSerializer):
    statut_libelle = serializers.CharField(source="get_statut_display", read_only=True)

    class Meta:
        model = Reservation
        fields = (
            "numero", "statut", "statut_libelle", "nom", "telephone",
            "date_heure", "nb_personnes", "note", "commentaire_restaurant", "date_creation",
        )


class ChangementStatutReservationSerializer(serializers.Serializer):
    statut = serializers.ChoiceField(choices=Reservation.Statut.choices)
    commentaire = serializers.CharField(required=False, allow_blank=True, max_length=255)