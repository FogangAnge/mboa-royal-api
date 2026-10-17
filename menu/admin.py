from django.contrib import admin
from django.utils.html import format_html

from .models import Categorie, GroupeOptions, Option, Plat


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ("nom", "nom_en", "ordre", "est_active")
    list_editable = ("ordre", "est_active")


class GroupeOptionsInline(admin.TabularInline):
    model = GroupeOptions
    extra = 0
    show_change_link = True
    fields = ("nom", "nom_en", "obligatoire", "choix_multiple", "ordre")


@admin.register(Plat)
class PlatAdmin(admin.ModelAdmin):
    list_display = ("apercu", "nom", "categorie", "prix", "est_actif", "est_disponible", "est_vedette")
    list_display_links = ("apercu", "nom")
    list_editable = ("prix", "est_actif", "est_disponible", "est_vedette")
    list_filter = ("categorie", "est_actif", "est_disponible", "est_vedette")
    search_fields = ("nom", "nom_en", "region_origine")
    list_select_related = ("categorie",)
    inlines = [GroupeOptionsInline]
    actions = ["marquer_epuise", "remettre_disponible"]

    fieldsets = (
        ("Le plat", {"fields": ("categorie", "nom", "nom_en", "region_origine", "prix", "photo")}),
        ("Descriptions", {"fields": ("description", "description_en")}),
        ("Affichage", {"fields": ("est_actif", "est_disponible", "est_vedette", "ordre")}),
        ("Jours proposés", {"fields": (
            ("lundi", "mardi", "mercredi", "jeudi"),
            ("vendredi", "samedi", "dimanche"),
        )}),
    )

    @admin.display(description="photo")
    def apercu(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width:48px;height:48px;object-fit:cover;border-radius:8px">',
                obj.photo.url,
            )
        return "—"

    @admin.action(description="Marquer comme épuisé aujourd'hui")
    def marquer_epuise(self, request, queryset):
        nombre = queryset.update(est_disponible=False)
        self.message_user(request, f"{nombre} plat(s) marqué(s) comme épuisé(s).")

    @admin.action(description="Remettre en disponibilité")
    def remettre_disponible(self, request, queryset):
        nombre = queryset.update(est_disponible=True)
        self.message_user(request, f"{nombre} plat(s) de nouveau disponible(s).")


class OptionInline(admin.TabularInline):
    model = Option
    extra = 1
    fields = ("nom", "nom_en", "supplement", "est_disponible", "ordre")


@admin.register(GroupeOptions)
class GroupeOptionsAdmin(admin.ModelAdmin):
    list_display = ("nom", "plat", "obligatoire", "choix_multiple")
    list_filter = ("plat",)
    inlines = [OptionInline]