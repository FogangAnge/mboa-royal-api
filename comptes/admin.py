from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = (
        "telephone", "nom", "role", "disponible", "est_bloque", "is_active", "date_inscription",
    )
    list_filter = ("role", "disponible", "est_bloque", "is_active", "langue")
    search_fields = ("telephone", "nom", "email")
    ordering = ("-date_inscription",)

    fieldsets = (
        (None, {"fields": ("telephone", "password")}),
        ("Informations", {"fields": ("nom", "email", "langue")}),
        ("Rôle et statut", {"fields": ("role", "disponible", "est_bloque", "is_active")}),
        (
            "Accès à l'admin Django",
            {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Dates", {"fields": ("last_login", "date_inscription")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("telephone", "nom", "role", "password1", "password2"),
            },
        ),
    )