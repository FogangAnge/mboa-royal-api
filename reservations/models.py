from django.conf import settings
from django.db import models
from django.utils import timezone

from restaurants.models import Restaurant


class TransitionInvalide(Exception):
    """Levée quand un changement de statut n'est pas permis."""


class Reservation(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente de confirmation"
        CONFIRMEE = "confirmee", "Confirmée"
        REFUSEE = "refusee", "Refusée"
        ANNULEE = "annulee", "Annulée"
        HONOREE = "honoree", "Client venu"
        ABSENT = "absent", "Client absent"

    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name="reservations", verbose_name="restaurant"
    )
    numero = models.CharField("numéro", max_length=20, unique=True, null=True, editable=False)
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reservations", verbose_name="compte client",
    )
    nom = models.CharField("nom", max_length=150)
    telephone = models.CharField("téléphone", max_length=20)
    date_heure = models.DateTimeField("date et heure")
    nb_personnes = models.PositiveSmallIntegerField("nombre de personnes")
    note = models.CharField("note", max_length=500, blank=True)
    statut = models.CharField(
        "statut", max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE
    )
    commentaire_restaurant = models.CharField("réponse du restaurant", max_length=255, blank=True)
    traitee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reservations_traitees", verbose_name="traitée par",
    )
    date_creation = models.DateTimeField("demandée le", auto_now_add=True)
    date_modification = models.DateTimeField("modifiée le", auto_now=True)

    class Meta:
        verbose_name = "réservation"
        verbose_name_plural = "réservations"
        ordering = ["date_heure"]

    def __str__(self):
        return self.numero or "Nouvelle réservation"

    def save(self, *args, **kwargs):
        creation = self.pk is None
        super().save(*args, **kwargs)
        if creation and not self.numero:
            self.numero = f"RES-{self.pk:04d}"
            super().save(update_fields=["numero"])

    def changer_statut(self, nouveau, auteur=None, commentaire=""):
        if nouveau not in TRANSITIONS.get(self.statut, set()):
            raise TransitionInvalide(
                f"Impossible de passer de « {self.get_statut_display()} » "
                f"à « {Reservation.Statut(nouveau).label} »."
            )
        if nouveau in (Reservation.Statut.HONOREE, Reservation.Statut.ABSENT):
            if self.date_heure > timezone.now():
                raise TransitionInvalide("On ne peut noter la venue du client qu'après l'heure réservée.")
        self.statut = nouveau
        self.traitee_par = auteur
        if commentaire:
            self.commentaire_restaurant = commentaire
        self.save(update_fields=["statut", "traitee_par", "commentaire_restaurant", "date_modification"])


TRANSITIONS = {
    Reservation.Statut.EN_ATTENTE: {
        Reservation.Statut.CONFIRMEE, Reservation.Statut.REFUSEE, Reservation.Statut.ANNULEE,
    },
    Reservation.Statut.CONFIRMEE: {
        Reservation.Statut.HONOREE, Reservation.Statut.ABSENT, Reservation.Statut.ANNULEE,
    },
}