"""
Évaluation des performances du système multi-agents (livrable n°4 du CDC).

Mesure, sur un jeu de tâches de référence : latence de bout en bout, taux de
succès, nombre de messages échangés entre agents, et respect du seuil de 60 s
fixé par le critère d'acceptance de l'US-01.

USAGE
-----
    python -m tests.benchmark_performances                 # contre l'API locale
    python -m tests.benchmark_performances --prod          # contre l'URL publique Azure

Le script lit API_KEY_VALUE depuis le fichier .env : aucune clé n'est écrite en
dur ni affichée dans la sortie.

SORTIE
------
    - un tableau récapitulatif dans le terminal
    - un fichier benchmark_resultats.json (données brutes, horodatées)
    - un bloc LaTeX prêt à coller dans la section 12.2 du rapport
"""

import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
import os

load_dotenv()

URL_LOCALE = "http://localhost:8000"
URL_PROD = "https://smartovate-mas-api.calmglacier-34682c28.francecentral.azurecontainerapps.io"

SEUIL_US01_SECONDES = 60
INTERVALLE_POLLING = 2.0
TIMEOUT_GLOBAL = 300

# Jeu de tâches de référence — volontairement hétérogène en difficulté
JEU_DE_TEST = [
    ("T1", "Écris une fonction Python qui calcule la suite de Fibonacci."),
    ("T2", "Écris une fonction Python qui vérifie si une chaîne est un palindrome."),
    ("T3", "Écris une fonction Python qui trie une liste de dictionnaires par une clé donnée."),
    ("T4", "Écris une fonction Python qui calcule la factorielle d'un entier, avec gestion des cas limites."),
    ("T5", "Écris une fonction Python qui fusionne deux listes triées en une seule liste triée."),
]


def executer_tache(client, base_url, api_key, identifiant, enonce):
    """Soumet une tâche, attend sa complétion, retourne les métriques mesurées."""
    entetes = {"x-api-key": api_key}
    resultat = {
        "id": identifiant,
        "tache": enonce,
        "statut_final": None,
        "duree_s": None,
        "nb_messages": None,
        "succes": False,
        "erreur": None,
    }

    debut = time.perf_counter()
    try:
        reponse = client.post(f"{base_url}/tasks", json={"task": enonce}, headers=entetes, timeout=30)
        reponse.raise_for_status()
        task_id = reponse.json()["task_id"]

        while True:
            if time.perf_counter() - debut > TIMEOUT_GLOBAL:
                resultat["erreur"] = f"timeout après {TIMEOUT_GLOBAL}s"
                resultat["statut_final"] = "TIMEOUT"
                break

            suivi = client.get(f"{base_url}/tasks/{task_id}", headers=entetes, timeout=30)
            suivi.raise_for_status()
            corps = suivi.json()
            statut = corps.get("statut")

            if statut == "TERMINE":
                resultat["statut_final"] = "TERMINE"
                resultat["succes"] = True
                resultat["nb_messages"] = len(corps.get("messages", []) or [])
                break
            if statut == "ERREUR":
                resultat["statut_final"] = "ERREUR"
                resultat["erreur"] = corps.get("erreur", "non précisée")
                break

            time.sleep(INTERVALLE_POLLING)

    except Exception as exc:
        resultat["erreur"] = f"{type(exc).__name__}: {exc}"
        resultat["statut_final"] = resultat["statut_final"] or "EXCEPTION"

    resultat["duree_s"] = round(time.perf_counter() - debut, 2)
    return resultat


def generer_bloc_latex(resultats, stats):
    """Produit le tableau LaTeX à coller dans la section 12.2 du rapport."""
    lignes = []
    for r in resultats:
        statut = "Succès" if r["succes"] else "Échec"
        duree = f"{r['duree_s']:.1f}" if r["duree_s"] is not None else "---"
        msgs = r["nb_messages"] if r["nb_messages"] is not None else "---"
        lignes.append(f"{r['id']} & {duree} & {msgs} & {statut} \\\\")

    corps = "\n".join(lignes)
    return f"""
\\begin{{longtable}}[]{{@{{}}llll@{{}}}}
\\toprule
\\textbf{{Tâche}} & \\textbf{{Durée (s)}} & \\textbf{{Messages}} & \\textbf{{Résultat}} \\\\
\\midrule
\\endhead
{corps}
\\bottomrule
\\end{{longtable}}

Sur les {stats['total']} tâches du jeu de référence, {stats['succes']} se sont conclues par un
statut \\texttt{{TERMINE}}, soit un taux de succès de {stats['taux_succes']:.0f}~\\%. La latence
médiane s'établit à {stats['mediane']:.1f}~secondes, pour un minimum de {stats['min']:.1f}~s et
un maximum de {stats['max']:.1f}~s. {stats['sous_seuil']} des {stats['total']} exécutions
respectent le seuil de soixante secondes fixé par le critère d'acceptance de l'US-01.
"""


def main():
    parseur = argparse.ArgumentParser(description="Benchmark de performances du MAS")
    parseur.add_argument("--prod", action="store_true", help="cibler l'URL publique Azure")
    args = parseur.parse_args()

    base_url = URL_PROD if args.prod else URL_LOCALE
    api_key = os.getenv("API_KEY_VALUE")
    if not api_key:
        raise SystemExit("API_KEY_VALUE absente du .env — abandon.")

    environnement = "production (Azure Container Apps)" if args.prod else "local"
    print(f"\nÉvaluation des performances — environnement {environnement}")
    print(f"Cible : {base_url}")
    print(f"Jeu de test : {len(JEU_DE_TEST)} tâches\n")

    resultats = []
    with httpx.Client() as client:
        for identifiant, enonce in JEU_DE_TEST:
            print(f"  [{identifiant}] en cours...", end=" ", flush=True)
            r = executer_tache(client, base_url, api_key, identifiant, enonce)
            resultats.append(r)
            marque = "OK" if r["succes"] else "ECHEC"
            print(f"{marque} — {r['duree_s']}s")

    durees_ok = [r["duree_s"] for r in resultats if r["succes"]]
    nb_succes = len(durees_ok)
    stats = {
        "total": len(resultats),
        "succes": nb_succes,
        "taux_succes": 100 * nb_succes / len(resultats) if resultats else 0,
        "mediane": statistics.median(durees_ok) if durees_ok else 0,
        "min": min(durees_ok) if durees_ok else 0,
        "max": max(durees_ok) if durees_ok else 0,
        "sous_seuil": sum(1 for d in durees_ok if d < SEUIL_US01_SECONDES),
    }

    print("\n" + "=" * 60)
    print(f"Taux de succès    : {stats['succes']}/{stats['total']} ({stats['taux_succes']:.0f} %)")
    print(f"Latence médiane   : {stats['mediane']:.1f} s")
    print(f"Latence min / max : {stats['min']:.1f} s / {stats['max']:.1f} s")
    print(f"Sous le seuil 60s : {stats['sous_seuil']}/{stats['total']}")
    print("=" * 60)

    sortie = {
        "horodatage": datetime.now(timezone.utc).isoformat(),
        "environnement": environnement,
        "url": base_url,
        "statistiques": stats,
        "resultats": resultats,
    }
    Path("benchmark_resultats.json").write_text(
        json.dumps(sortie, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    Path("benchmark_bloc_latex.txt").write_text(
        generer_bloc_latex(resultats, stats), encoding="utf-8"
    )

    print("\nFichiers produits :")
    print("  benchmark_resultats.json   (données brutes, à joindre en preuve)")
    print("  benchmark_bloc_latex.txt   (à coller dans la section 12.2 du rapport)")


if __name__ == "__main__":
    main()
