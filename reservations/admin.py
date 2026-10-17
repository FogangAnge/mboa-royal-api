from django.contrib import admin

from .models import Reservation, TransitionInvalide


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("numero", "date_heure", "nom", "telephone", "nb_personnes", "statut")
    list_filter = ("statut",)
    search_fields = ("numero", "nom", "telephone")
    date_hierarchy = "date_heure"
    readonly_fields = (
        "numero", "client", "statut", "traitee_par", "date_creation", "date_modification",
    )
    fields = (
        "numero", "statut", "date_heure", "nb_personnes", "nom", "telephone", "client",
        "note", "commentaire_restaurant", "traitee_par", "date_creation", "date_modification",
    )
    actions = ["confirmer", "refuser", "client_venu", "client_absent"]

    def _changer(self, request, queryset, statut):
        reussites, echecs = 0, []
        for reservation in queryset:
            try:
                reservation.changer_statut(statut, auteur=request.user)
                reussites += 1
            except TransitionInvalide as exc:
                echecs.append(f"{reservation.numero} : {exc}")
        if reussites:
            self.message_user(request, f"{reussites} réservation(s) mise(s) à jour.")
        for message in echecs:
            self.message_user(request, message, level="warning")

    @admin.action(description="Confirmer")
    def confirmer(self, request, queryset):
        self._changer(request, queryset, Reservation.Statut.CONFIRMEE)

    @admin.action(description="Refuser")
    def refuser(self, request, queryset):
        self._changer(request, queryset, Reservation.Statut.REFUSEE)

    @admin.action(description="Le client est venu")
    def client_venu(self, request, queryset):
        self._changer(request, queryset, Reservation.Statut.HONOREE)

    @admin.action(description="Le client est absent")
    def client_absent(self, request, queryset):
        self._changer(request, queryset, Reservation.Statut.ABSENT)