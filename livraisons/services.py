from django.db.models import Sum

from commandes.models import Commande, HistoriqueStatut

from .models import VersementLivreur


def courses_du_jour(restaurant, livreur, jour):
    """Les commandes livrées par ce livreur ce jour-là."""
    livrees_ce_jour = HistoriqueStatut.objects.filter(
        statut=Commande.Statut.LIVREE, date__date=jour
    ).values("commande_id")
    return Commande.objects.filter(
        restaurant=restaurant,
        livreur=livreur,
        statut=Commande.Statut.LIVREE,
        pk__in=livrees_ce_jour,
    )


def bilan_livreur(restaurant, livreur, jour):
    courses = courses_du_jour(restaurant, livreur, jour)
    encaisse = courses.aggregate(total=Sum("montant_encaisse"))["total"] or 0
    verse = VersementLivreur.objects.filter(
        restaurant=restaurant, livreur=livreur, jour=jour
    ).aggregate(total=Sum("montant"))["total"] or 0
    return {
        "livreur": livreur.id,
        "nom": livreur.nom or livreur.telephone,
        "telephone": livreur.telephone,
        "disponible": livreur.disponible,
        "nb_courses": courses.count(),
        "encaisse": encaisse,
        "verse": verse,
        "reste_a_verser": encaisse - verse,
    }