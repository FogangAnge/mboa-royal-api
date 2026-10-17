from rest_framework import serializers

from restaurants.utils import get_restaurant_actif

from .models import Categorie, GroupeOptions, Option, Plat


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ("id", "nom", "nom_en", "supplement", "est_disponible")


class GroupeOptionsSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = GroupeOptions
        fields = ("id", "nom", "nom_en", "obligatoire", "choix_multiple", "options")


class PlatSerializer(serializers.ModelSerializer):
    categorie_nom = serializers.CharField(source="categorie.nom", read_only=True)
    groupes_options = GroupeOptionsSerializer(many=True, read_only=True)
    jours_proposes = serializers.SerializerMethodField()
    propose_aujourdhui = serializers.SerializerMethodField()
    commandable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Plat
        fields = (
            "id", "categorie", "categorie_nom",
            "nom", "nom_en", "description", "description_en", "region_origine",
            "prix", "photo",
            "est_actif", "est_disponible", "est_vedette", "ordre",
            "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche",
            "jours_proposes", "propose_aujourdhui", "commandable",
            "groupes_options",
        )

    def get_jours_proposes(self, obj):
        return obj.jours_proposes()

    def get_propose_aujourdhui(self, obj):
        return obj.est_propose_le()

    def validate_categorie(self, categorie):
        if categorie.restaurant_id != get_restaurant_actif().id:
            raise serializers.ValidationError("Cette catégorie n'appartient pas à ce restaurant.")
        return categorie


class CategorieMenuSerializer(serializers.ModelSerializer):
    plats = PlatSerializer(source="plats_visibles", many=True, read_only=True)

    class Meta:
        model = Categorie
        fields = ("id", "nom", "nom_en", "plats")