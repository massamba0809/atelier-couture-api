"""Tableau de bord d'avancement : quelles routes de l'énoncé existent déjà dans l'API ?

Usage (depuis la racine du projet) :
    python -m scripts.avancement

Ne touche pas à la base de données : il lit seulement les routes enregistrées
dans l'application. Les responsables ci-dessous sont une PROPOSITION de
répartition : modifiez-les ici si vous changez d'avis (puis régénérez
docs/SUIVI.md à la main).
"""
import os
from collections import defaultdict

# Variables factices : on n'ouvre aucune connexion, on inspecte juste les routes.
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "cle-pour-avancement")
os.environ.setdefault("ADMIN_PASSWORD", "x")

M, S = "Massamba", "Sine"

# (n°, méthode, chemin complet, rôle, palier, responsable)
ROUTES: list[tuple[int, str, str, str, int, str]] = [
    (1, "POST", "/api/v1/auth/login", "Public", 1, M),
    (2, "GET", "/api/v1/auth/me", "Connecté", 1, M),
    (3, "POST", "/api/v1/utilisateurs", "Admin", 1, M),
    (4, "GET", "/api/v1/utilisateurs", "Admin", 1, M),
    (5, "GET", "/api/v1/utilisateurs/{id}", "Admin", 1, M),
    (6, "PATCH", "/api/v1/utilisateurs/{id}", "Admin", 1, M),
    (7, "POST", "/api/v1/clients", "Tous", 1, M),
    (8, "GET", "/api/v1/clients", "Tous", 1, M),
    (9, "GET", "/api/v1/clients/{id}", "Tous", 1, M),
    (10, "PATCH", "/api/v1/clients/{id}", "Tous", 1, M),
    (11, "DELETE", "/api/v1/clients/{id}", "Admin", 1, M),
    (12, "GET", "/api/v1/clients/{id}/commandes", "Tous", 1, M),
    (13, "GET", "/api/v1/clients/{id}/resume", "Tous", 1, M),
    (14, "POST", "/api/v1/catalogue", "Admin", 1, M),
    (15, "GET", "/api/v1/catalogue", "Tous", 1, M),
    (16, "GET", "/api/v1/catalogue/{id}", "Tous", 1, M),
    (17, "PATCH", "/api/v1/catalogue/{id}", "Admin", 1, M),
    (18, "POST", "/api/v1/clients/{id}/mesures", "Tailleur", 2, S),
    (19, "GET", "/api/v1/clients/{id}/mesures", "Tous", 2, S),
    (20, "GET", "/api/v1/clients/{id}/mesures/derniere", "Tous", 2, S),
    (21, "GET", "/api/v1/mesures/{id}", "Tous", 2, S),
    (22, "PATCH", "/api/v1/mesures/{id}", "Tailleur", 2, S),
    (23, "DELETE", "/api/v1/mesures/{id}", "Tailleur", 2, S),
    (24, "POST", "/api/v1/commandes", "Accueil", 2, M),
    (25, "GET", "/api/v1/commandes", "Tous", 2, M),
    (26, "GET", "/api/v1/commandes/{id}", "Tous", 2, M),
    (27, "PATCH", "/api/v1/commandes/{id}", "Accueil", 2, M),
    (28, "POST", "/api/v1/commandes/{id}/statut", "Tous (RG13-14)", 2, M),
    (29, "GET", "/api/v1/commandes/{id}/historique", "Tous", 2, M),
    (30, "POST", "/api/v1/commandes/{id}/lignes", "Accueil", 2, M),
    (31, "DELETE", "/api/v1/commandes/{id}/lignes/{ligne_id}", "Accueil", 2, M),
    (32, "POST", "/api/v1/commandes/{id}/paiements", "Accueil", 2, S),
    (33, "GET", "/api/v1/commandes/{id}/paiements", "Tous", 2, S),
    (34, "DELETE", "/api/v1/paiements/{id}", "Admin", 2, S),
    (35, "PUT", "/api/v1/commandes/{id}/livraison", "Accueil", 3, S),
    (36, "GET", "/api/v1/commandes/{id}/livraison", "Tous", 3, S),
    (37, "POST", "/api/v1/commandes/{id}/livraison/confirmer", "Accueil", 3, S),
    (38, "GET", "/api/v1/livraisons", "Tous", 3, S),
    (39, "GET", "/api/v1/statistiques/tableau-de-bord", "Admin", 3, S),
    (40, "GET", "/api/v1/statistiques/chiffre-affaires", "Admin", 3, S),
    (41, "GET", "/api/v1/statistiques/types-vetement", "Admin", 3, S),
    (42, "GET", "/api/v1/statistiques/top-clients", "Admin", 3, S),
    (43, "GET", "/api/v1/statistiques/impayes", "Admin", 3, S),
    (44, "GET", "/health", "Public", 3, S),
]


def _normaliser(chemin: str) -> str:
    """{client_id}, {commande_id}... -> {id}, pour comparer avec l'énoncé."""
    import re

    morceaux = re.split(r"(\{[^}]+\})", chemin)
    return "".join(
        "{ligne_id}" if m == "{ligne_id}" else ("{id}" if m.startswith("{") else m) for m in morceaux
    )


def routes_presentes() -> set[tuple[str, str]]:
    from app.main import app

    # Le schéma OpenAPI liste toutes les routes, quelle que soit la version de FastAPI.
    presentes = set()
    for chemin, operations in app.openapi()["paths"].items():
        for methode in operations:
            presentes.add((methode.upper(), _normaliser(chemin)))
    return presentes


def main() -> None:
    presentes = routes_presentes()
    par_personne: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    par_palier: dict[int, list[int]] = defaultdict(lambda: [0, 0])

    print(f"{'N°':>3}  {'':1}  {'Méthode':<7} {'Chemin':<52} {'Palier':>6}  Responsable")
    print("-" * 90)
    for n, methode, chemin, _role, palier, resp in ROUTES:
        fait = (methode, chemin) in presentes
        par_personne[resp][1] += 1
        par_palier[palier][1] += 1
        if fait:
            par_personne[resp][0] += 1
            par_palier[palier][0] += 1
        print(f"{n:>3}  {'✓' if fait else '·'}  {methode:<7} {chemin:<52} {palier:>6}  {resp}")

    total = sum(v[0] for v in par_personne.values())
    print("-" * 90)
    print(f"Routes enregistrées : {total}/{len(ROUTES)}")
    for palier in sorted(par_palier):
        f, t = par_palier[palier]
        print(f"  Palier {palier} : {f}/{t}")
    for resp, (f, t) in par_personne.items():
        print(f"  {resp:<9}: {f}/{t}")
    print("\n(« enregistrée » = la route existe ; vérifiez aussi ses règles de gestion et ses tests.)")


if __name__ == "__main__":
    main()
