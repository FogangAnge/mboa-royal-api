from django.db import transaction
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from comptes.permissions import EstPersonnel
from comptes.serializers import normaliser_telephone
from restaurants.utils import get_restaurant_actif

from .models import Commande, HistoriqueStatut, TransitionInvalide
from .serializers import (
    AssignationSerializer,
    ChangementStatutSerializer,
    CommandeCreationSerializer,
    CommandeSerializer,
    PaiementSerializer,
    SuiviSerializer,
)
from .whatsapp import lien_whatsapp


class CommandeViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    POST /api/commandes/                       passer une commande (avec ou sans compte)
    GET  /api/commandes/                       mes commandes / toutes / mes courses, selon le rôle
    GET  /api/commandes/<numero>/              détail
    POST /api/commandes/<numero>/statut/       faire avancer la commande
    POST /api/commandes/<numero>/assigner/     choisir le livreur (personnel)
    POST /api/commandes/<numero>/paiement/     enregistrer le paiement (personnel)
    """

    lookup_field = "numero"

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        if self.action in ("assigner", "paiement"):
            return [EstPersonnel()]
        return [IsAuthenticated()]

    def get_throttles(self):
        if self.action == "create":
            self.throttle_scope = "commande"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def get_serializer_class(self):
        if self.action == "create":
            return CommandeCreationSerializer
        return CommandeSerializer

    def get_queryset(self):
        commandes = (
            Commande.objects.filter(restaurant=get_restaurant_actif())
            .select_related("restaurant", "livreur", "client")
            .prefetch_related("lignes", "historique")
        )
        user = self.request.user
        if user.est_personnel:
            statut = self.request.query_params.get("statut")
            return commandes.filter(statut=statut) if statut else commandes
        if user.est_livreur:
            return commandes.filter(livreur=user)
        return commandes.filter(client=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        commande = serializer.save()

        reponse = CommandeSerializer(commande, context=self.get_serializer_context()).data
        reponse["code_livraison"] = commande.code_livraison
        reponse["lien_whatsapp"] = lien_whatsapp(commande)
        return Response(reponse, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def statut(self, request, numero=None):
        """POST /api/commandes/<numero>/statut/ : faire avancer la commande."""
        entree = ChangementStatutSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        nouveau = entree.validated_data["statut"]
        commande = self.get_object()
        self._verifier_droit_statut(request.user, commande, nouveau)

        erreur = None
        with transaction.atomic():
            commande = Commande.objects.select_for_update().get(pk=commande.pk)
            try:
                commande.changer_statut(
                    nouveau,
                    auteur=request.user,
                    commentaire=entree.validated_data.get("commentaire", ""),
                    code=entree.validated_data.get("code"),
                    montant_encaisse=entree.validated_data.get("montant_encaisse"),
                    mode_paiement=entree.validated_data.get("mode_paiement"),
                )
            except TransitionInvalide as exc:
                erreur = str(exc)
        if erreur:
            raise ValidationError({"detail": erreur})
        return Response(CommandeSerializer(self.get_object(), context=self.get_serializer_context()).data)

    def _verifier_droit_statut(self, user, commande, nouveau):
        if user.est_personnel:
            return
        if user.est_livreur:
            if nouveau not in (Commande.Statut.EN_LIVRAISON, Commande.Statut.LIVREE):
                raise PermissionDenied("Un livreur peut seulement démarrer ou terminer une livraison.")
            return
        # Client : annuler sa commande tant qu'elle n'est pas confirmée
        if nouveau != Commande.Statut.ANNULEE or commande.statut != Commande.Statut.EN_ATTENTE:
            raise PermissionDenied(
                "Vous pouvez seulement annuler votre commande, tant qu'elle n'est pas confirmée."
            )

    @action(detail=True, methods=["post"])
    def assigner(self, request, numero=None):
        """POST /api/commandes/<numero>/assigner/ : choisir le livreur."""
        entree = AssignationSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        commande = self.get_object()
        if commande.mode != Commande.Mode.LIVRAISON:
            raise ValidationError({"detail": "Une commande à emporter n'a pas de livreur."})
        modifiables = (Commande.Statut.CONFIRMEE, Commande.Statut.EN_PREPARATION, Commande.Statut.PRETE)
        if commande.statut not in modifiables:
            raise ValidationError({"detail": "On ne peut plus changer le livreur de cette commande."})

        livreur = entree.validated_data["livreur"]
        commande.livreur = livreur
        commande.save(update_fields=["livreur", "date_modification"])
        HistoriqueStatut.objects.create(
            commande=commande, statut=commande.statut, auteur=request.user,
            commentaire=f"Livreur assigné : {livreur.nom or livreur.telephone}",
        )
        return Response(CommandeSerializer(self.get_object(), context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"])
    def paiement(self, request, numero=None):
        """POST /api/commandes/<numero>/paiement/ : enregistrer le paiement."""
        entree = PaiementSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        commande = self.get_object()
        commande.mode_paiement = entree.validated_data["mode_paiement"]
        commande.est_payee = entree.validated_data["est_payee"]
        commande.save(update_fields=["mode_paiement", "est_payee", "date_modification"])
        return Response(CommandeSerializer(commande, context=self.get_serializer_context()).data)


class SuiviCommandeView(generics.GenericAPIView):
    """GET /api/commandes/suivi/?numero=MR-0001&telephone=677123456"""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "suivi"
    serializer_class = SuiviSerializer

    def get(self, request):
        numero = request.query_params.get("numero", "").strip().upper()
        try:
            telephone = normaliser_telephone(request.query_params.get("telephone", ""))
        except ValidationError:
            telephone = None

        commande = None
        if numero and telephone:
            commande = (
                Commande.objects.filter(
                    restaurant=get_restaurant_actif(), numero=numero, telephone_client=telephone
                )
                .select_related("livreur")
                .prefetch_related("lignes", "historique")
                .first()
            )
        if commande is None:
            raise NotFound("Aucune commande ne correspond à ce numéro et à ce téléphone.")
        return Response(self.get_serializer(commande).data)