from django.core.management.base import BaseCommand
from django.db import transaction

from restaurants.models import Restaurant
from zones.models import Quartier, Region, Ville, ZoneLivraison

GEOGRAPHIE = {
    "Adamaoua": {"Ngaoundéré": []},
    "Centre": {
        "Yaoundé": [
            "Bastos", "Biyem-Assi", "Emana", "Essos", "Melen",
            "Mokolo", "Mvan", "Ngousso", "Nlongkak", "Omnisport",
        ],
    },
    "Est": {"Bertoua": []},
    "Extrême-Nord": {"Maroua": []},
    "Littoral": {
        "Douala": [
            "Akwa", "Bali", "Bépanda", "Bonabéri", "Bonamoussadi", "Bonanjo",
            "Bonapriso", "Cité des Palmiers", "Deido", "Kotto", "Logbessou",
            "Logpom", "Makepe", "Ndogbong", "Ndokoti", "New Bell", "Village", "Yassa",
        ],
        "Edéa": [],
        "Nkongsamba": [],
    },
    "Nord": {"Garoua": []},
    "Nord-Ouest": {"Bamenda": []},
    "Ouest": {"Bafoussam": []},
    "Sud": {"Ebolowa": []},
    "Sud-Ouest": {"Buea": [], "Kumba": [], "Limbe": []},
}


class Command(BaseCommand):
    help = "Charge les régions, villes et quartiers du Cameroun, puis prépare les zones de livraison."

    @transaction.atomic
    def handle(self, *args, **options):
        nb_regions = nb_villes = nb_quartiers = 0

        for nom_region, villes in GEOGRAPHIE.items():
            region, cree = Region.objects.get_or_create(nom=nom_region)
            nb_regions += cree
            for nom_ville, quartiers in villes.items():
                ville, cree = Ville.objects.get_or_create(region=region, nom=nom_ville)
                nb_villes += cree
                for nom_quartier in quartiers:
                    _, cree = Quartier.objects.get_or_create(ville=ville, nom=nom_quartier)
                    nb_quartiers += cree

        self.stdout.write(self.style.SUCCESS(
            f"Ajoutés : {nb_regions} régions, {nb_villes} villes, {nb_quartiers} quartiers."
        ))

        restaurant = Restaurant.objects.filter(est_actif=True).first()
        if restaurant is None:
            self.stdout.write(self.style.WARNING(
                "Aucun restaurant actif : les zones de livraison n'ont pas été préparées."
            ))
            return

        nb_zones = 0
        for quartier in Quartier.objects.filter(ville__nom__iexact=restaurant.ville):
            _, cree = ZoneLivraison.objects.get_or_create(
                restaurant=restaurant,
                quartier=quartier,
                defaults={"frais": 0, "delai_min": 45, "est_active": False},
            )
            nb_zones += cree

        self.stdout.write(self.style.SUCCESS(
            f"{nb_zones} zones de livraison préparées pour {restaurant.nom} ({restaurant.ville}). "
            "Réglez leurs frais et activez-les dans l'admin."
        ))