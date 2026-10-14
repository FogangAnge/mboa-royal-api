from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UtilisateurManager(BaseUserManager):
    """Sait créer des utilisateurs à partir d'un numéro de téléphone."""

    use_in_migrations = True

    def _create_user(self, telephone, password, **extra_fields):
        if not telephone:
            raise ValueError("Le numéro de téléphone est obligatoire.")
        user = self.model(telephone=telephone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, telephone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(telephone, password, **extra_fields)

    def create_superuser(self, telephone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Utilisateur.Role.PROPRIETAIRE)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Un superutilisateur doit avoir is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Un superutilisateur doit avoir is_superuser=True.")
        return self._create_user(telephone, password, **extra_fields)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    """Un compte de la plateforme : propriétaire, gérant, livreur ou client."""

    class Role(models.TextChoices):
        PROPRIETAIRE = "proprietaire", "Propriétaire"
        GERANT = "gerant", "Gérant"
        LIVREUR = "livreur", "Livreur"
        CLIENT = "client", "Client"

    class Langue(models.TextChoices):
        FRANCAIS = "fr", "Français"
        ANGLAIS = "en", "English"

    telephone = models.CharField("téléphone", max_length=20, unique=True)
    nom = models.CharField("nom complet", max_length=150, blank=True)
    email = models.EmailField("adresse e-mail", blank=True)
    role = models.CharField("rôle", max_length=20, choices=Role.choices, default=Role.CLIENT)
    langue = models.CharField("langue", max_length=2, choices=Langue.choices, default=Langue.FRANCAIS)
    est_bloque = models.BooleanField(
        "bloqué",
        default=False,
        help_text="Un client bloqué ne peut plus passer de commande.",
    )
    is_active = models.BooleanField("actif", default=True)
    is_staff = models.BooleanField(
        "accès à l'admin Django",
        default=False,
        help_text="Autorise la connexion à l'interface d'administration Django.",
    )
    date_inscription = models.DateTimeField("date d'inscription", default=timezone.now)

    objects = UtilisateurManager()

    USERNAME_FIELD = "telephone"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        ordering = ["-date_inscription"]

    def __str__(self):
        return f"{self.nom or self.telephone} ({self.get_role_display()})"

    @property
    def est_personnel(self):
        """Vrai pour le propriétaire et le gérant (accès à l'espace admin du restaurant)."""
        return self.role in {self.Role.PROPRIETAIRE, self.Role.GERANT}

    @property
    def est_livreur(self):
        return self.role == self.Role.LIVREUR


from django.db import models

# Create your models here.
