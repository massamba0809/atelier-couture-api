"""Règles de gestion des clients.

Responsable : Massamba (RG1). Le reste du service (création, doublons,
suppression RG4...) est à compléter.
"""
import re

from app.core.errors import DonneesInvalides

_SEPARATEURS = re.compile(r"[\s.\-()]")
_FORME_VALIDE = re.compile(r"^\+?\d{6,20}$")


def normaliser_telephone(brut: str) -> str:
    """RG1 : « 77 123 45 67 » et « 771234567 » désignent le même client.

    Supprime espaces, points, tirets et parenthèses ; valide 6 à 20 chiffres
    avec un « + » initial facultatif. Lève DonneesInvalides (422) sinon.
    """
    nettoye = _SEPARATEURS.sub("", brut or "")
    if not _FORME_VALIDE.match(nettoye):
        raise DonneesInvalides(
            "Numéro de téléphone invalide : 6 à 20 chiffres, « + » initial facultatif."
        )
    return nettoye
