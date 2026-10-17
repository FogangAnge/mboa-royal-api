from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from comptes.models import Utilisateur
from comptes.serializers import normaliser_telephone
from menu.models import Plat
from restaurants.utils import get_restaurant_actif
from zones.models import ZoneLivraison

from .models import Commande, HistoriqueStatut, LigneCommande

MAX_COMMANDES_EN_ATTENTE = 2


# ---------- Ce que le client envoie ----------

class LigneEntreeSerializer(serializers.Serializer):
    plat = serializers.PrimaryKeyRelatedField(queryset=Plat.objects.all())
    quantite = serializers.IntegerField(min_value=1, max_value=50)
    options = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )


class CommandeCreationSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=Commande.Mode.choices)
    zone_livraison = serializers.PrimaryKeyRelatedField(
        queryset=ZoneLivraison.objects.select_related("quartier__ville"),
        required=False, allow_null=True,
    )
    repere = serializers.CharField(required=False, allow_blank=True, max_length=255)
    nom_client = serializers.CharField(required=False, max_length=150)
    telephone_client = serializers.CharField(required=False, max_length=20)
    heure_souhaitee = serializers.DateTimeField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)
    lignes = LigneEntreeSerializer(many=True)

    def validate_telephone_client(self, valeur):
        return normaliser_telephone(valeur)

    def validate(self, data):
        user = self.context["request"].user
        restaurant = get_restaurant_actif()
        self._valider_client(data, user, restaurant)
        moment = self._valider_moment(data, restaurant)
        self._valider_retrait(data, restaurant)
        self._valider_lignes(data, restaurant, moment)
        return data

    # --- Qui commande ? ---
    def _valider_client(self, data, user, restaurant):
        if user.is_authenticated:
            if user.est_bloque:
                raise serializers.ValidationError(
                    "Ce compte ne peut pas passer de commande. Contactez le restaurant."
                )
            data.setdefault("nom_client", user.nom or user.telephone)
            data.setdefault("telephone_client", user.telephone)
        else:
            erreurs = {}
            if not data.get("nom_client"):
                erreurs["nom_client"] = "Indiquez votre nom."
            if not data.get("telephone_client"):
                erreurs["telephone_client"] = "Indiquez votre numéro de téléphone."
            if erreurs:
                raise serializers.ValidationError(erreurs)

        telephone = data["telephone_client"]
        if Utilisateur.objects.filter(telephone=telephone, est_bloque=True).exists():
            raise serializers.ValidationError(
                "Ce numéro ne peut pas passer de commande. Contactez le restaurant."
            )
        en_attente = Commande.objects.filter(
            restaurant=restaurant, telephone_client=telephone, statut=Commande.Statut.EN_ATTENTE
        ).count()
        if en_attente >= MAX_COMMANDES_EN_ATTENTE:
            raise serializers.ValidationError(
                "Vous avez déjà des commandes en attente de confirmation. "
                "Merci d'attendre notre réponse sur WhatsApp."
            )

    # --- Pour quand ? ---
    def _valider_moment(self, data, restaurant):
        maintenant = timezone.now()
        heure = data.get("heure_souhaitee")
        if heure is None:
            if not restaurant.est_ouvert(maintenant):
                raise serializers.ValidationError(
                    "Le restaurant est fermé pour le moment. "
                    "Vous pouvez programmer votre commande pour plus tard."
                )
            return maintenant

        delai = timedelta(minutes=restaurant.delai_preparation_min)
        if heure < maintenant + delai:
            raise serializers.ValidationError({
                "heure_souhaitee": f"Choisissez une heure au moins {restaurant.delai_preparation_min} "
                                   "minutes après maintenant."
            })
        if heure > maintenant + timedelta(days=7):
            raise serializers.ValidationError({
                "heure_souhaitee": "On ne peut pas programmer une commande plus de 7 jours à l'avance."
            })
        if not restaurant.est_ouvert(heure):
            raise serializers.ValidationError({
                "heure_souhaitee": "Le restaurant est fermé à cette heure-là."
            })
        return heure

    # --- Livraison ou à emporter ? ---
    def _valider_retrait(self, data, restaurant):
        if data["mode"] == Commande.Mode.EMPORTER:
            data["zone_livraison"] = None
            return
        zone = data.get("zone_livraison")
        if zone is None:
            raise serializers.ValidationError({"zone_livraison": "Choisissez votre quartier de livraison."})
        if zone.restaurant_id != restaurant.id or not zone.est_active:
            raise serializers.ValidationError({"zone_livraison": "Nous ne livrons pas encore ce quartier."})

    # --- Quels plats ? ---
    def _valider_lignes(self, data, restaurant, moment):
        if not data["lignes"]:
            raise serializers.ValidationError({"lignes": "Votre panier est vide."})

        pour_aujourdhui = timezone.localdate(moment) == timezone.localdate()
        lignes_validees = []
        sous_total = 0
        for ligne in data["lignes"]:
            plat = ligne["plat"]
            if plat.restaurant_id != restaurant.id or not plat.est_actif:
                raise serializers.ValidationError({"lignes": f"« {plat.nom} » n'est pas au menu."})
            if pour_aujourdhui and not plat.est_disponible:
                raise serializers.ValidationError({"lignes": f"« {plat.nom} » est épuisé aujourd'hui."})
            if not plat.est_propose_le(moment):
                raise serializers.ValidationError(
                    {"lignes": f"« {plat.nom} » n'est pas proposé ce jour-là."}
                )

            options, supplement = self._valider_options(plat, ligne["options"])
            prix_unitaire = plat.prix + supplement
            lignes_validees.append({
                "plat": plat,
                "nom_plat": plat.nom,
                "prix_unitaire": prix_unitaire,
                "quantite": ligne["quantite"],
                "options": options,
            })
            sous_total += prix_unitaire * ligne["quantite"]

        data["lignes_validees"] = lignes_validees
        data["sous_total"] = sous_total

    def _valider_options(self, plat, ids_choisis):
        groupes = list(plat.groupes_options.prefetch_related("options"))
        ids_choisis = set(ids_choisis)
        ids_connus = {option.id for groupe in groupes for option in groupe.options.all()}
        if ids_choisis - ids_connus:
            raise serializers.ValidationError(
                {"lignes": f"Option invalide pour « {plat.nom} »."}
            )

        choisies, supplement = [], 0
        for groupe in groupes:
            selection = [option for option in groupe.options.all() if option.id in ids_choisis]
            if groupe.obligatoire and not selection:
                raise serializers.ValidationError(
                    {"lignes": f"Choisissez : {groupe.nom.lower()} pour « {plat.nom} »."}
                )
            if not groupe.choix_multiple and len(selection) > 1:
                raise serializers.ValidationError(
                    {"lignes": f"Un seul choix possible pour : {groupe.nom.lower()} (« {plat.nom} »)."}
                )
            for option in selection:
                if not option.est_disponible:
                    raise serializers.ValidationError(
                        {"lignes": f"« {option.nom} » n'est plus disponible."}
                    )
                choisies.append({"groupe": groupe.nom, "option": option.nom, "supplement": option.supplement})
                supplement += option.supplement
        return choisies, supplement

    # --- Enregistrement ---
    @transaction.atomic
    def create(self, data):
        user = self.context["request"].user
        zone = data.get("zone_livraison")
        frais = zone.frais if zone else 0

        commande = Commande.objects.create(
            restaurant=get_restaurant_actif(),
            client=user if user.is_authenticated else None,
            nom_client=data["nom_client"],
            telephone_client=data["telephone_client"],
            mode=data["mode"],
            zone_livraison=zone,
            quartier=zone.quartier.nom if zone else "",
            ville=zone.quartier.ville.nom if zone else "",
            repere=data.get("repere", ""),
            heure_souhaitee=data.get("heure_souhaitee"),
            note=data.get("note", ""),
            sous_total=data["sous_total"],
            frais_livraison=frais,
            total=data["sous_total"] + frais,
        )
        LigneCommande.objects.bulk_create(
            [LigneCommande(commande=commande, **ligne) for ligne in data["lignes_validees"]]
        )
        HistoriqueStatut.objects.create(
            commande=commande,
            statut=commande.statut,
            auteur=user if user.is_authenticated else None,
            commentaire="Commande passée en ligne.",
        )
        return commande


# ---------- Ce que l'API renvoie ----------

class LigneCommandeSerializer(serializers.ModelSerializer):
    sous_total = serializers.IntegerField(read_only=True)

    class Meta:
        model = LigneCommande
        fields = ("plat", "nom_plat", "quantite", "prix_unitaire", "options", "sous_total")


class HistoriqueStatutSerializer(serializers.ModelSerializer):
    statut_libelle = serializers.CharField(source="get_statut_display", read_only=True)

    class Meta:
        model = HistoriqueStatut
        fields = ("statut", "statut_libelle", "commentaire", "date")


class CommandeSerializer(serializers.ModelSerializer):
    statut_libelle = serializers.CharField(source="get_statut_display", read_only=True)
    lignes = LigneCommandeSerializer(many=True, read_only=True)
    historique = HistoriqueStatutSerializer(many=True, read_only=True)
    livreur_nom = serializers.CharField(source="livreur.nom", read_only=True, default=None)
    code_livraison = serializers.SerializerMethodField()

    class Meta:
        model = Commande
        fields = (
            "numero", "statut", "statut_libelle", "mode",
            "nom_client", "telephone_client", "quartier", "ville", "repere",
            "heure_souhaitee", "note", "lignes",
            "sous_total", "frais_livraison", "total",
            "mode_paiement", "est_payee", "montant_encaisse", "livreur_nom", "code_livraison",
            "historique", "date_creation",
        )

    def get_code_livraison(self, obj):
        """Le code n'est montré qu'au client qui a passé la commande."""
        user = self.context["request"].user
        if user.is_authenticated and obj.client_id == user.id:
            return obj.code_livraison
        return None


# ---------- Actions sur une commande ----------

class ChangementStatutSerializer(serializers.Serializer):
    statut = serializers.ChoiceField(choices=Commande.Statut.choices)
    commentaire = serializers.CharField(required=False, allow_blank=True, max_length=255)
    code = serializers.CharField(required=False, allow_blank=True, max_length=4)
    montant_encaisse = serializers.IntegerField(required=False, min_value=0)
    mode_paiement = serializers.ChoiceField(
        choices=[Commande.ModePaiement.ESPECES, Commande.ModePaiement.MOBILE_MONEY], required=False
    )


class AssignationSerializer(serializers.Serializer):
    livreur = serializers.PrimaryKeyRelatedField(
        queryset=Utilisateur.objects.filter(role=Utilisateur.Role.LIVREUR, is_active=True)
    )


class PaiementSerializer(serializers.Serializer):
    mode_paiement = serializers.ChoiceField(choices=Commande.ModePaiement.choices)
    est_payee = serializers.BooleanField()


class SuiviSerializer(serializers.ModelSerializer):
    """Ce qu'un visiteur voit en suivant sa commande : jamais le code."""

    statut_libelle = serializers.CharField(source="get_statut_display", read_only=True)
    lignes = LigneCommandeSerializer(many=True, read_only=True)
    historique = HistoriqueStatutSerializer(many=True, read_only=True)
    livreur = serializers.SerializerMethodField()

    class Meta:
        model = Commande
        fields = (
            "numero", "statut", "statut_libelle", "mode", "quartier", "ville",
            "heure_souhaitee", "lignes", "total", "livreur", "historique", "date_creation",
        )

    def get_livreur(self, obj):
        if obj.statut == Commande.Statut.EN_LIVRAISON and obj.livreur:
            return {"nom": obj.livreur.nom, "telephone": obj.livreur.telephone}
        return None