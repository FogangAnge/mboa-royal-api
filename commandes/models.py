import secrets

from django.conf import settings
from django.db import models

from menu.models import Plat
from restaurants.models import Restaurant
from zones.models import ZoneLivraison


def generer_code_livraison():
    """Un code à 4 chiffres, tiré au hasard de façon sûre."""
    return f"{secrets.randbelow(10000):04d}"


MAX_TENTATIVES_CODE = 5


class TransitionInvalide(Exception):
    """Levée quand un changement de statut n'est pas permis."""


class Commande(models.Model):
    class Mode(models.TextChoices):
        LIVRAISON = "livraison", "Livraison"
        EMPORTER = "emporter", "À emporter"

    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente de confirmation"
        CONFIRMEE = "confirmee", "Confirmée"
        EN_PREPARATION = "en_preparation", "En préparation"
        PRETE = "prete", "Prête"
        EN_LIVRAISON = "en_livraison", "En livraison"
        LIVREE = "livree", "Livrée"
        ANNULEE = "annulee", "Annulée"

    class ModePaiement(models.TextChoices):
        A_DEFINIR = "a_definir", "À définir (WhatsApp)"
        ESPECES = "especes", "Espèces"
        MOBILE_MONEY = "mobile_money", "Mobile Money"

    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name="commandes", verbose_name="restaurant"
    )
    numero = models.CharField("numéro", max_length=20, unique=True, null=True, editable=False)

    # Le client
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="commandes", verbose_name="compte client",
    )
    nom_client = models.CharField("nom du client", max_length=150)
    telephone_client = models.CharField("téléphone du client", max_length=20)

    # Le retrait
    mode = models.CharField("mode", max_length=20, choices=Mode.choices)
    zone_livraison = models.ForeignKey(
        ZoneLivraison, on_delete=models.PROTECT, null=True, blank=True,
        related_name="commandes", verbose_name="zone de livraison",
    )
    quartier = models.CharField("quartier", max_length=100, blank=True)
    ville = models.CharField("ville", max_length=100, blank=True)
    repere = models.CharField("point de repère", max_length=255, blank=True)
    heure_souhaitee = models.DateTimeField(
        "heure souhaitée", null=True, blank=True, help_text="Vide : dès que possible."
    )
    note = models.TextField("note du client", blank=True)

    # Les montants (en FCFA), figés au moment de la commande
    sous_total = models.PositiveIntegerField("sous-total", default=0)
    frais_livraison = models.PositiveIntegerField("frais de livraison", default=0)
    total = models.PositiveIntegerField("total", default=0)

    # Le suivi
    statut = models.CharField(
        "statut", max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE
    )
    mode_paiement = models.CharField(
        "mode de paiement", max_length=20, choices=ModePaiement.choices, default=ModePaiement.A_DEFINIR
    )
    est_payee = models.BooleanField("payée", default=False)
    code_livraison = models.CharField(
        "code de livraison", max_length=4, default=generer_code_livraison, editable=False
    )
    livreur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="livraisons", verbose_name="livreur", limit_choices_to={"role": "livreur"},
    )
    tentatives_code = models.PositiveSmallIntegerField("essais de code ratés", default=0)
    montant_encaisse = models.PositiveIntegerField(
        "montant encaissé par le livreur", null=True, blank=True
    )

    date_creation = models.DateTimeField("passée le", auto_now_add=True)
    date_modification = models.DateTimeField("modifiée le", auto_now=True)

    class Meta:
        verbose_name = "commande"
        verbose_name_plural = "commandes"
        ordering = ["-date_creation"]

    def __str__(self):
        return self.numero or "Nouvelle commande"

    def save(self, *args, **kwargs):
        creation = self.pk is None
        super().save(*args, **kwargs)
        if creation and not self.numero:
            initiales = "".join(mot[0] for mot in self.restaurant.nom.split()[:2]).upper()
            self.numero = f"{initiales}-{self.pk:04d}"
            super().save(update_fields=["numero"])

    def changer_statut(self, nouveau, auteur=None, commentaire="", code=None,
                       montant_encaisse=None, mode_paiement=None):
        """Fait avancer la commande en respectant les règles, et l'inscrit dans l'historique."""
        if nouveau not in TRANSITIONS.get(self.statut, set()):
            raise TransitionInvalide(
                f"Impossible de passer de « {self.get_statut_display()} » "
                f"à « {Commande.Statut(nouveau).label} »."
            )

        if nouveau == Commande.Statut.EN_LIVRAISON:
            if self.mode != Commande.Mode.LIVRAISON:
                raise TransitionInvalide("Une commande à emporter ne part pas en livraison.")
            if self.livreur_id is None:
                raise TransitionInvalide("Assignez d'abord un livreur à cette commande.")

        if nouveau == Commande.Statut.LIVREE:
            if self.mode == Commande.Mode.LIVRAISON and self.statut != Commande.Statut.EN_LIVRAISON:
                raise TransitionInvalide("La commande doit d'abord partir en livraison.")
            self._verifier_code(code)
            if montant_encaisse is not None:
                self.montant_encaisse = montant_encaisse
                self.est_payee = True
                if mode_paiement:
                    self.mode_paiement = mode_paiement

        self.statut = nouveau
        self.save(update_fields=[
            "statut", "tentatives_code", "montant_encaisse", "est_payee",
            "mode_paiement", "date_modification",
        ])
        HistoriqueStatut.objects.create(
            commande=self, statut=nouveau, auteur=auteur, commentaire=commentaire
        )

    def _verifier_code(self, code):
        if self.tentatives_code >= MAX_TENTATIVES_CODE:
            raise TransitionInvalide(
                "Trop d'essais de code incorrects. Contactez le restaurant pour débloquer la commande."
            )
        if (code or "").strip() != self.code_livraison:
            self.tentatives_code += 1
            self.save(update_fields=["tentatives_code"])
            restants = MAX_TENTATIVES_CODE - self.tentatives_code
            raise TransitionInvalide(f"Code de livraison incorrect. Essais restants : {restants}.")


class LigneCommande(models.Model):
    commande = models.ForeignKey(
        Commande, on_delete=models.CASCADE, related_name="lignes", verbose_name="commande"
    )
    plat = models.ForeignKey(
        Plat, on_delete=models.PROTECT, related_name="lignes_commande", verbose_name="plat"
    )
    nom_plat = models.CharField("plat", max_length=120)
    prix_unitaire = models.PositiveIntegerField("prix unitaire (options comprises)")
    quantite = models.PositiveSmallIntegerField("quantité")
    options = models.JSONField("options choisies", default=list, blank=True)

    class Meta:
        verbose_name = "ligne de commande"
        verbose_name_plural = "lignes de commande"

    def __str__(self):
        return f"{self.quantite} × {self.nom_plat}"

    @property
    def sous_total(self):
        return self.prix_unitaire * self.quantite


class HistoriqueStatut(models.Model):
    commande = models.ForeignKey(
        Commande, on_delete=models.CASCADE, related_name="historique", verbose_name="commande"
    )
    statut = models.CharField("statut", max_length=20, choices=Commande.Statut.choices)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="par"
    )
    commentaire = models.CharField("commentaire", max_length=255, blank=True)
    date = models.DateTimeField("date", auto_now_add=True)

    class Meta:
        verbose_name = "changement de statut"
        verbose_name_plural = "historique des statuts"
        ordering = ["date"]

    def __str__(self):
        return f"{self.commande} → {self.get_statut_display()}"


TRANSITIONS = {
    Commande.Statut.EN_ATTENTE: {Commande.Statut.CONFIRMEE, Commande.Statut.ANNULEE},
    Commande.Statut.CONFIRMEE: {Commande.Statut.EN_PREPARATION, Commande.Statut.ANNULEE},
    Commande.Statut.EN_PREPARATION: {Commande.Statut.PRETE, Commande.Statut.ANNULEE},
    Commande.Statut.PRETE: {
        Commande.Statut.EN_LIVRAISON, Commande.Statut.LIVREE, Commande.Statut.ANNULEE,
    },
    Commande.Statut.EN_LIVRAISON: {Commande.Statut.LIVREE},
}