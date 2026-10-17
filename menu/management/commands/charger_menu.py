from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from menu.models import Categorie, GroupeOptions, Option, Plat
from restaurants.models import Restaurant

DOSSIER_PHOTOS = Path(settings.BASE_DIR) / "seed" / "plats"

CATEGORIES = [
    ("Plats en sauce", "Stews & sauces"),
    ("Cuits en feuilles", "Leaf-wrapped dishes"),
    ("Volaille & grillades", "Poultry & grills"),
    ("Petit-déjeuner", "Breakfast"),
]

PIMENT = ("Piment", "Chili", [
    ("Sans piment", "No chili"),
    ("Piment à part", "Chili on the side"),
    ("Pimenté", "Spicy"),
])

PLATS = [
    {
        "nom": "Ndolé royal", "nom_en": "Royal ndolé",
        "categorie": "Plats en sauce", "region": "Littoral", "photo": "ndole.jpg", "vedette": True,
        "description": "Le plat national : feuilles de ndolé mijotées à la pâte d'arachide, "
                       "relevées de crevettes sautées et d'oignons.",
        "description_en": "Cameroon's national dish: ndolé leaves simmered in peanut paste, "
                          "topped with sautéed prawns and onions.",
        "accompagnements": [("Miondo", "Miondo"), ("Plantain mûr frit", "Fried ripe plantain"),
                            ("Plantain vapeur", "Steamed plantain"), ("Bâton de manioc", "Cassava stick")],
        "piment": True,
    },
    {
        "nom": "Poulet DG", "nom_en": "Poulet DG",
        "categorie": "Volaille & grillades", "region": "Littoral", "photo": "poulet-dg.jpg", "vedette": True,
        "description": "Le plat des grandes occasions : poulet doré, plantains mûrs frits "
                       "et légumes croquants.",
        "description_en": "The dish for special occasions: golden chicken, fried ripe plantain "
                          "and crunchy vegetables.",
        "accompagnements": [], "piment": True,
    },
    {
        "nom": "Taro sauce jaune", "nom_en": "Taro with yellow soup",
        "categorie": "Plats en sauce", "region": "Ouest", "photo": "taro.jpg", "vedette": True,
        "description": "Taro pilé servi avec la sauce jaune à l'huile de palme, "
                       "accompagnée de viande et de tripes.",
        "description_en": "Pounded taro served with palm-oil yellow soup, with beef and tripe.",
        "accompagnements": [], "piment": True,
    },
    {
        "nom": "Eru & water fufu", "nom_en": "Eru & water fufu",
        "categorie": "Plats en sauce", "region": "Sud-Ouest", "photo": "eru.jpg", "vedette": True,
        "description": "Feuilles d'eru et de waterleaf mijotées à l'huile de palme, "
                       "avec viande, poisson fumé et peau de bœuf.",
        "description_en": "Eru and waterleaf simmered in palm oil with meat, smoked fish and cow skin.",
        "accompagnements": [("Water fufu", "Water fufu"), ("Garri", "Garri")],
        "piment": True,
    },
    {
        "nom": "Koki", "nom_en": "Koki",
        "categorie": "Cuits en feuilles", "region": "Ouest", "photo": "koki.jpg", "vedette": False,
        "description": "Gâteau de haricots cornille écrasés à l'huile de palme, "
                       "cuit à la vapeur dans des feuilles de bananier.",
        "description_en": "Black-eyed bean cake with red palm oil, steamed in banana leaves.",
        "accompagnements": [("Plantain vapeur", "Steamed plantain"), ("Plantain mûr", "Ripe plantain")],
        "piment": True,
    },
    {
        "nom": "Bongo tchobi", "nom_en": "Mbongo tchobi",
        "categorie": "Plats en sauce", "region": "Littoral", "photo": "bongo.jpg", "vedette": True,
        "description": "Poisson mijoté dans la sauce noire mbongo, parfumée aux épices grillées.",
        "description_en": "Fish simmered in black mbongo sauce, flavoured with roasted spices.",
        "accompagnements": [("Plantain vapeur", "Steamed plantain"), ("Bâton de manioc", "Cassava stick")],
        "piment": True,
    },
    {
        "nom": "BHB", "nom_en": "BHB (puff-puff, beans & porridge)",
        "categorie": "Petit-déjeuner", "region": "Tout le Cameroun", "photo": "bhb.jpg", "vedette": False,
        "description": "Beignets, haricots et bouillie : le petit-déjeuner populaire de nos quartiers.",
        "description_en": "Puff-puff, beans and porridge: the favourite street breakfast.",
        "accompagnements": [], "piment": True,
    },
    {
        "nom": "Mets de pistache", "nom_en": "Pistachio (egusi) pudding",
        "categorie": "Cuits en feuilles", "region": "Centre", "photo": "pistache.jpg", "vedette": False,
        "description": "Graines de courge écrasées, mêlées au poisson fumé et cuites en paquets de feuilles.",
        "description_en": "Ground squash seeds with smoked fish, cooked in leaf parcels.",
        "accompagnements": [("Bâton de manioc", "Cassava stick"), ("Plantain vapeur", "Steamed plantain")],
        "piment": True,
    },
    {
        "nom": "Okok", "nom_en": "Okok",
        "categorie": "Plats en sauce", "region": "Centre", "photo": "okok.jpg", "vedette": False,
        "description": "Feuilles d'okok finement coupées, cuites au jus de noix de palme et à l'arachide.",
        "description_en": "Finely shredded okok leaves cooked with palm-nut juice and peanuts.",
        "accompagnements": [("Bâton de manioc", "Cassava stick"), ("Plantain vapeur", "Steamed plantain")],
        "piment": False,
    },
]


class Command(BaseCommand):
    help = "Crée les catégories et les plats de départ (désactivés, prix à 0), avec leurs photos."

    @transaction.atomic
    def handle(self, *args, **options):
        restaurant = Restaurant.objects.filter(est_actif=True).first()
        if restaurant is None:
            raise CommandError("Aucun restaurant actif : créez-le d'abord dans l'admin.")

        categories = {}
        for ordre, (nom, nom_en) in enumerate(CATEGORIES, start=1):
            categorie, _ = Categorie.objects.get_or_create(
                restaurant=restaurant, nom=nom, defaults={"nom_en": nom_en, "ordre": ordre}
            )
            categories[nom] = categorie

        nb_crees = nb_photos = 0
        for ordre, data in enumerate(PLATS, start=1):
            plat, cree = Plat.objects.get_or_create(
                restaurant=restaurant,
                nom=data["nom"],
                defaults={
                    "nom_en": data["nom_en"],
                    "categorie": categories[data["categorie"]],
                    "region_origine": data["region"],
                    "description": data["description"],
                    "description_en": data["description_en"],
                    "prix": 0,
                    "est_actif": False,
                    "est_vedette": data["vedette"],
                    "ordre": ordre,
                },
            )
            if not cree:
                continue
            nb_crees += 1

            chemin = DOSSIER_PHOTOS / data["photo"]
            if chemin.exists():
                with chemin.open("rb") as fichier:
                    plat.photo.save(data["photo"], File(fichier), save=True)
                nb_photos += 1
            else:
                self.stdout.write(self.style.WARNING(f"Photo introuvable : {chemin}"))

            if data["accompagnements"]:
                groupe = GroupeOptions.objects.create(
                    plat=plat, nom="Accompagnement", nom_en="Side dish", ordre=1
                )
                for position, (nom, nom_en) in enumerate(data["accompagnements"]):
                    Option.objects.create(groupe=groupe, nom=nom, nom_en=nom_en, ordre=position)

            if data["piment"]:
                nom, nom_en, choix = PIMENT
                groupe = GroupeOptions.objects.create(plat=plat, nom=nom, nom_en=nom_en, ordre=2)
                for position, (nom, nom_en) in enumerate(choix):
                    Option.objects.create(groupe=groupe, nom=nom, nom_en=nom_en, ordre=position)

        self.stdout.write(self.style.SUCCESS(
            f"{nb_crees} plats créés, dont {nb_photos} avec photo. "
            "Fixez leurs prix puis rendez-les visibles dans l'admin."
        ))