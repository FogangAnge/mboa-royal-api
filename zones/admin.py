from django.contrib import admin

from .models import Quartier, Region, Ville, ZoneLivraison


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    search_fields = ("nom",)


@admin.register(Ville)
class VilleAdmin(admin.ModelAdmin):
    list_display = ("nom", "region")
    list_filter = ("region",)
    search_fields = ("nom",)


@admin.register(Quartier)
class QuartierAdmin(admin.ModelAdmin):
    list_display = ("nom", "ville")
    list_filter = ("ville__region", "ville")
    search_fields = ("nom", "ville__nom")


@admin.register(ZoneLivraison)
class ZoneLivraisonAdmin(admin.ModelAdmin):
    list_display = ("quartier", "ville", "frais", "delai_min", "est_active")
    list_editable = ("frais", "delai_min", "est_active")
    list_filter = ("est_active", "quartier__ville")
    search_fields = ("quartier__nom", "quartier__ville__nom")
    autocomplete_fields = ("quartier",)
    list_select_related = ("quartier__ville",)

    @admin.display(description="ville", ordering="quartier__ville__nom")
    def ville(self, obj):
        return obj.quartier.ville