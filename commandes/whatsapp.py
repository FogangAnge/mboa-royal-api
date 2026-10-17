import re
from urllib.parse import quote


def numero_international(numero):
    """Transforme 6XXXXXXXX en 2376XXXXXXXX, le format attendu par wa.me."""
    chiffres = re.sub(r"\D", "", numero or "")
    if len(chiffres) == 9:
        chiffres = "237" + chiffres
    return chiffres


def message_commande(commande):
    lignes = [f"Bonjour {commande.restaurant.nom}, voici ma commande N° {commande.numero} :", ""]
    for ligne in commande.lignes.all():
        details = ", ".join(choix["option"] for choix in ligne.options)
        lignes.append(
            f"• {ligne.quantite} × {ligne.nom_plat}" + (f" ({details})" if details else "")
        )
    lignes.append("")
    if commande.mode == commande.Mode.LIVRAISON:
        adresse = f"{commande.quartier}, {commande.ville}"
        if commande.repere:
            adresse += f" — {commande.repere}"
        lignes.append(f"Livraison : {adresse}")
    else:
        lignes.append("À emporter")
    if commande.heure_souhaitee:
        lignes.append(f"Pour le : {commande.heure_souhaitee.astimezone():%d/%m à %H:%M}")
    lignes += [
        f"Sous-total : {commande.sous_total} {commande.restaurant.devise}",
        f"Livraison : {commande.frais_livraison} {commande.restaurant.devise}",
        f"Total : {commande.total} {commande.restaurant.devise}",
        "",
        f"Nom : {commande.nom_client} — Tél : {commande.telephone_client}",
        "Merci de confirmer ma commande.",
    ]
    return "\n".join(lignes)


def lien_whatsapp(commande):
    numero = numero_international(commande.restaurant.whatsapp)
    return f"https://wa.me/{numero}?text={quote(message_commande(commande))}"