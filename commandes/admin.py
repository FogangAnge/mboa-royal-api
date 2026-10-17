from django.contrib import admin

from .models import Commande, HistoriqueStatut, LigneCommande, TransitionInvalide


class LigneCommandeInline(admin.TabularInline):
    model = LigneCommande
    extra = 0
    can_delete = False
    readonly_fields = ("nom_plat", "quantite", "prix_unitaire", "options")
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


class HistoriqueStatutInline(admin.TabularInline):
    model = HistoriqueStatut
    extra = 0
    can_delete = False
    readonly_fields = ("date", "statut", "auteur", "commentaire")
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = (
        "numero", "nom_client", "telephone_client", "mode", "quartier",
        "total", "statut", "est_payee", "livreur", "date_creation",
    )
    list_filter = ("statut", "mode", "est_payee", "mode_paiement")
    search_fields = ("numero", "nom_client", "telephone_client")
    date_hierarchy = "date_creation"
    list_select_related = ("livreur",)
    inlines = [LigneCommandeInline, HistoriqueStatutInline]
    readonly_fields = (
        "numero", "client", "nom_client", "telephone_client", "mode", "zone_livraison",
        "quartier", "ville", "repere", "heure_souhaitee", "note",
        "sous_total", "frais_livraison", "total", "code_livraison",
        "date_creation", "date_modification",
        "statut", "tentatives_code", "montant_encaisse",
    )
    fieldsets = (
        ("Commande", {"fields": ("numero", "statut", "date_creation", "date_modification")}),
        ("Client", {"fields": ("client", "nom_client", "telephone_client", "note")}),
        ("Retrait", {"fields": ("mode", "zone_livraison", "quartier", "ville", "repere", "heure_souhaitee")}),
        ("Montants", {"fields": ("sous_total", "frais_livraison", "total")}),
        ("Paiement et livraison", {"fields": (
            "mode_paiement", "est_payee", "livreur", "code_livraison",
            "tentatives_code", "montant_encaisse",
        )}),
    )

    actions = ["confirmer", "mettre_en_preparation", "marquer_prete", "annuler"]

    def _changer(self, request, queryset, statut):
        reussites, echecs = 0, []
        for commande in queryset:
            try:
                commande.changer_statut(statut, auteur=request.user, commentaire="Depuis l'admin")
                reussites += 1
            except TransitionInvalide as exc:
                echecs.append(f"{commande.numero} : {exc}")
        if reussites:
            self.message_user(request, f"{reussites} commande(s) mise(s) à jour.")
        for message in echecs:
            self.message_user(request, message, level="warning")

    @admin.action(description="Confirmer")
    def confirmer(self, request, queryset):
        self._changer(request, queryset, Commande.Statut.CONFIRMEE)

    @admin.action(description="Passer en préparation")
    def mettre_en_preparation(self, request, queryset):
        self._changer(request, queryset, Commande.Statut.EN_PREPARATION)

    @admin.action(description="Marquer comme prête")
    def marquer_prete(self, request, queryset):
        self._changer(request, queryset, Commande.Statut.PRETE)

    @admin.action(description="Annuler")
    def annuler(self, request, queryset):
        self._changer(request, queryset, Commande.Statut.ANNULEE)