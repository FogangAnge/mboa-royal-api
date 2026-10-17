from django.db import models

from restaurants.models import Restaurant


class Region(models.Model):
    nom = models.CharField("nom", max_length=80, unique=True)

    class Meta:
        verbose_name = "région"
        verbose_name_plural = "régions"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Ville(models.Model):
    region = models.ForeignKey(
        Region, on_delete=models.PROTECT, related_name="villes", verbose_name="région"
    )
    nom = models.CharField("nom", max_length=100)

    class Meta:
        verbose_name = "ville"
        verbose_name_plural = "villes"
        ordering = ["nom"]
        constraints = [
            models.UniqueConstraint(fields=["region", "nom"], name="ville_unique_par_region"),
        ]

    def __str__(self):
        return self.nom


class Quartier(models.Model):
    ville = models.ForeignKey(
        Ville, on_delete=models.PROTECT, related_name="quartiers", verbose_name="ville"
    )
    nom = models.CharField("nom", max_length=100)

    class Meta:
        verbose_name = "quartier"
        verbose_name_plural = "quartiers"
        ordering = ["ville__nom", "nom"]
        constraints = [
            models.UniqueConstraint(fields=["ville", "nom"], name="quartier_unique_par_ville"),
        ]

    def __str__(self):
        return f"{self.nom} ({self.ville.nom})"


class ZoneLivraison(models.Model):
    """Un quartier livré par un restaurant, avec ses conditions."""

    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name="zones_livraison", verbose_name="restaurant"
    )
    quartier = models.ForeignKey(
        Quartier, on_delete=models.PROTECT, related_name="zones_livraison", verbose_name="quartier"
    )
    frais = models.PositiveIntegerField("frais de livraison (FCFA)", default=0)
    delai_min = models.PositiveIntegerField("délai de livraison (minutes)", default=45)
    est_active = models.BooleanField("livraison ouverte", default=True)

    class Meta:
        verbose_name = "zone de livraison"
        verbose_name_plural = "zones de livraison"
        ordering = ["quartier__ville__nom", "quartier__nom"]
        constraints = [
            models.UniqueConstraint(fields=["restaurant", "quartier"], name="une_zone_par_quartier"),
        ]

    def __str__(self):
        return f"{self.quartier} — {self.frais} FCFA"