from django.contrib import admin

from .models import HoraireOuverture, Restaurant


class HoraireOuvertureInline(admin.TabularInline):
    model = HoraireOuverture
    extra = 7
    max_num = 7


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ("nom", "ville", "whatsapp", "est_actif")
    inlines = [HoraireOuvertureInline]
    fieldsets = (
        ("Identité", {"fields": ("nom", "slogan", "description", "logo")}),
        ("Localisation", {"fields": ("pays", "ville", "quartier", "adresse", "latitude", "longitude")}),
        ("Contact", {"fields": ("telephone", "whatsapp", "email")}),
        ("Apparence", {"fields": ("couleur_principale", "couleur_accent")}),
        ("Fonctionnement", {"fields": ("capacite_salle", "delai_preparation_min", "devise", "est_actif")}),
    )


from django.contrib import admin

# Register your models here.
