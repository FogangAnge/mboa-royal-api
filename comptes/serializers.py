import re

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Utilisateur


def normaliser_telephone(valeur: str) -> str:
    """Ramène un numéro camerounais au format 6XXXXXXXX (9 chiffres)."""
    numero = re.sub(r"[\s.\-]", "", valeur)
    if numero.startswith("+237"):
        numero = numero[4:]
    elif numero.startswith("00237"):
        numero = numero[5:]
    elif numero.startswith("237") and len(numero) == 12:
        numero = numero[3:]
    if not re.fullmatch(r"6\d{8}", numero):
        raise serializers.ValidationError(
            "Numéro invalide : il doit contenir 9 chiffres et commencer par 6."
        )
    return numero


class UtilisateurSerializer(serializers.ModelSerializer):
    """Les informations d'un compte, telles qu'on les renvoie dans l'API."""

    class Meta:
        model = Utilisateur
        fields = ("id", "telephone", "nom", "email", "role", "langue", "date_inscription")
        read_only_fields = fields


class InscriptionSerializer(serializers.ModelSerializer):
    """Crée un compte client à partir d'un téléphone et d'un mot de passe."""

    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = Utilisateur
        fields = ("telephone", "nom", "email", "langue", "password")

    def validate_telephone(self, valeur):
        numero = normaliser_telephone(valeur)
        if Utilisateur.objects.filter(telephone=numero).exists():
            raise serializers.ValidationError("Un compte existe déjà avec ce numéro.")
        return numero

    def validate_password(self, valeur):
        validate_password(valeur)
        return valeur

    def create(self, validated_data):
        return Utilisateur.objects.create_user(
            role=Utilisateur.Role.CLIENT,
            **validated_data,
        )