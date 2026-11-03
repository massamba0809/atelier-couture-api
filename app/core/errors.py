"""Erreurs métier communes.

Les services lèvent ces exceptions (sans connaître HTTP) ; un handler dans
main.py les transforme en réponse {"detail": "message en français"}.

    raise Conflit("Le téléphone 771234567 existe déjà.")
"""


class ErreurMetier(Exception):
    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NonAuthentifie(ErreurMetier):
    status_code = 401


class Interdit(ErreurMetier):
    status_code = 403


class Introuvable(ErreurMetier):
    status_code = 404


class Conflit(ErreurMetier):
    status_code = 409


class DonneesInvalides(ErreurMetier):
    status_code = 422
