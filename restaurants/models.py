from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

valider_couleur = RegexValidator(
    r"^#[0-9A-Fa-f]{6}$", "La couleur doit être au format #RRGGBB (ex. #0F2A1D)."
)


class Restaurant(models.Model):
    """La carte d'identité du restaurant : tout ce qui n'est pas écrit en dur dans le code."""

    # Identité
    nom = models.CharField("nom", max_length=150)
    slogan = models.CharField("slogan", max_length=200, blank=True)
    description = models.TextField("description", blank=True)
    logo = models.ImageField("logo", upload_to="restaurants/logos/", blank=True)

    # Localisation
    pays = models.CharField("pays", max_length=80, default="Cameroun")
    ville = models.CharField("ville", max_length=100)
    quartier = models.CharField("quartier", max_length=100, blank=True)
    adresse = models.CharField("adresse", max_length=255)
    latitude = models.DecimalField("latitude", max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField("longitude", max_digits=9, decimal_places=6, null=True, blank=True)

    # Contact
    telephone = models.CharField("téléphone", max_length=20)
    whatsapp = models.CharField(
        "numéro WhatsApp", max_length=20, help_text="Le numéro qui reçoit les commandes."
    )
    email = models.EmailField("e-mail", blank=True)

    # Apparence
    couleur_principale = models.CharField(
        "couleur principale", max_length=7, default="#0F2A1D", validators=[valider_couleur]
    )
    couleur_accent = models.CharField(
        "couleur d'accent", max_length=7, default="#D4A24C", validators=[valider_couleur]
    )

    # Fonctionnement
    capacite_salle = models.PositiveIntegerField(
        "capacité de la salle", default=40, help_text="Nombre de places, pour les réservations."
    )
    delai_preparation_min = models.PositiveIntegerField(
        "délai de préparation (minutes)", default=30
    )
    devise = models.CharField("devise", max_length=10, default="FCFA")
    est_actif = models.BooleanField("actif", default=True)

    date_creation = models.DateTimeField("créé le", auto_now_add=True)
    date_modification = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        verbose_name = "restaurant"
        verbose_name_plural = "restaurants"

    def __str__(self):
        return f"{self.nom} — {self.ville}"

    def est_ouvert(self, moment=None):
        """Indique si le restaurant est ouvert à un moment donné (maintenant par défaut)."""
        moment = timezone.localtime(moment)
        for horaire in self.horaires.all():
            if horaire.jour == moment.weekday():
                return horaire.couvre(moment.time())
        return False


class HoraireOuverture(models.Model):
    """Les horaires d'un jour de la semaine."""

    class Jour(models.IntegerChoices):
        LUNDI = 0, "Lundi"
        MARDI = 1, "Mardi"
        MERCREDI = 2, "Mercredi"
        JEUDI = 3, "Jeudi"
        VENDREDI = 4, "Vendredi"
        SAMEDI = 5, "Samedi"
        DIMANCHE = 6, "Dimanche"

    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name="horaires", verbose_name="restaurant"
    )
    jour = models.PositiveSmallIntegerField("jour", choices=Jour.choices)
    ferme = models.BooleanField("fermé ce jour", default=False)
    ouverture = models.TimeField("ouverture", null=True, blank=True)
    fermeture = models.TimeField("fermeture", null=True, blank=True)

    class Meta:
        verbose_name = "horaire d'ouverture"
        verbose_name_plural = "horaires d'ouverture"
        ordering = ["jour"]
        constraints = [
            models.UniqueConstraint(fields=["restaurant", "jour"], name="un_horaire_par_jour"),
        ]

    def __str__(self):
        if self.ferme:
            return f"{self.get_jour_display()} : fermé"
        return f"{self.get_jour_display()} : {self.ouverture:%H:%M} – {self.fermeture:%H:%M}"

    def clean(self):
        if not self.ferme and (self.ouverture is None or self.fermeture is None):
            raise ValidationError("Indiquez l'heure d'ouverture et de fermeture, ou cochez « fermé ».")

    def couvre(self, heure):
        """Vrai si l'heure donnée tombe dans les horaires de ce jour."""
        if self.ferme or self.ouverture is None or self.fermeture is None:
            return False
        if self.ouverture <= self.fermeture:
            return self.ouverture <= heure < self.fermeture
        # Fermeture après minuit (ex. 18:00 – 01:00)
        return heure >= self.ouverture or heure < self.fermeture


from django.db import models

# Create your models here.
