from django.conf import settings
from django.db import models
from django.utils import timezone

from restaurants.models import Restaurant


class VersementLivreur(models.Model):
    """L'argent qu'un livreur remet au restaurant."""

    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name="versements", verbose_name="restaurant"
    )
    livreur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="versements",
        verbose_name="livreur", limit_choices_to={"role": "livreur"},
    )
    montant = models.PositiveIntegerField("montant versé (FCFA)")
    jour = models.DateField("journée concernée", default=timezone.localdate)
    recu_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="versements_recus", verbose_name="reçu par",
    )
    note = models.CharField("note", max_length=255, blank=True)
    date_creation = models.DateTimeField("enregistré le", auto_now_add=True)

    class Meta:
        verbose_name = "versement de livreur"
        verbose_name_plural = "versements des livreurs"
        ordering = ["-date_creation"]

    def __str__(self):
        return f"{self.livreur} — {self.montant} FCFA ({self.jour:%d/%m/%Y})"