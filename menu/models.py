from django.db import models
from django.utils import timezone

from restaurants.models import Restaurant

JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")


class Categorie(models.Model):
    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name="categories", verbose_name="restaurant"
    )
    nom = models.CharField("nom", max_length=100)
    nom_en = models.CharField("nom (anglais)", max_length=100, blank=True)
    ordre = models.PositiveSmallIntegerField("ordre d'affichage", default=0)
    est_active = models.BooleanField("visible", default=True)

    class Meta:
        verbose_name = "catégorie"
        verbose_name_plural = "catégories"
        ordering = ["ordre", "nom"]
        constraints = [
            models.UniqueConstraint(fields=["restaurant", "nom"], name="categorie_unique_par_restaurant"),
        ]

    def __str__(self):
        return self.nom


class Plat(models.Model):
    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name="plats", verbose_name="restaurant"
    )
    categorie = models.ForeignKey(
        Categorie, on_delete=models.PROTECT, related_name="plats", verbose_name="catégorie"
    )
    nom = models.CharField("nom", max_length=120)
    nom_en = models.CharField("nom (anglais)", max_length=120, blank=True)
    description = models.TextField("description", blank=True)
    description_en = models.TextField("description (anglais)", blank=True)
    region_origine = models.CharField("région d'origine", max_length=80, blank=True)
    prix = models.PositiveIntegerField("prix (FCFA)")
    photo = models.ImageField("photo", upload_to="plats/", blank=True)

    est_actif = models.BooleanField("visible sur le menu", default=True)
    est_disponible = models.BooleanField(
        "disponible aujourd'hui", default=True, help_text="Décochez quand le plat est épuisé."
    )
    est_vedette = models.BooleanField(
        "plat signature", default=False, help_text="Mis en avant sur la page d'accueil."
    )

    lundi = models.BooleanField("lundi", default=True)
    mardi = models.BooleanField("mardi", default=True)
    mercredi = models.BooleanField("mercredi", default=True)
    jeudi = models.BooleanField("jeudi", default=True)
    vendredi = models.BooleanField("vendredi", default=True)
    samedi = models.BooleanField("samedi", default=True)
    dimanche = models.BooleanField("dimanche", default=True)

    ordre = models.PositiveSmallIntegerField("ordre d'affichage", default=0)
    date_creation = models.DateTimeField("créé le", auto_now_add=True)
    date_modification = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        verbose_name = "plat"
        verbose_name_plural = "plats"
        ordering = ["categorie__ordre", "ordre", "nom"]
        constraints = [
            models.UniqueConstraint(fields=["restaurant", "nom"], name="plat_unique_par_restaurant"),
        ]

    def __str__(self):
        return self.nom

    def jours_proposes(self):
        """Liste des jours proposés : 0 = lundi … 6 = dimanche."""
        return [numero for numero, jour in enumerate(JOURS) if getattr(self, jour)]

    def est_propose_le(self, moment=None):
        numero = timezone.localtime(moment).weekday()
        return getattr(self, JOURS[numero])

    @property
    def commandable(self):
        """Le client peut-il le commander maintenant ?"""
        return self.est_actif and self.est_disponible and self.est_propose_le()


class GroupeOptions(models.Model):
    plat = models.ForeignKey(
        Plat, on_delete=models.CASCADE, related_name="groupes_options", verbose_name="plat"
    )
    nom = models.CharField("nom", max_length=80, help_text="Ex. : Accompagnement, Piment.")
    nom_en = models.CharField("nom (anglais)", max_length=80, blank=True)
    obligatoire = models.BooleanField("choix obligatoire", default=True)
    choix_multiple = models.BooleanField("plusieurs choix possibles", default=False)
    ordre = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "groupe d'options"
        verbose_name_plural = "groupes d'options"
        ordering = ["ordre", "id"]

    def __str__(self):
        return f"{self.plat.nom} — {self.nom}"


class Option(models.Model):
    groupe = models.ForeignKey(
        GroupeOptions, on_delete=models.CASCADE, related_name="options", verbose_name="groupe"
    )
    nom = models.CharField("nom", max_length=80)
    nom_en = models.CharField("nom (anglais)", max_length=80, blank=True)
    supplement = models.PositiveIntegerField("supplément (FCFA)", default=0)
    est_disponible = models.BooleanField("disponible", default=True)
    ordre = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "option"
        verbose_name_plural = "options"
        ordering = ["ordre", "id"]

    def __str__(self):
        return self.nom