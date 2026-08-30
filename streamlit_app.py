"""
Interface utilisateur Streamlit pour le systeme multi-agents Smartovate (US 3.2).

Cette interface :
  - permet de soumettre une tache en langage naturel au systeme multi-agents,
  - affiche en temps reel les echanges entre les agents (Orchestrateur, Codeur,
    Reviseur, Critique) pendant que la tache s'execute,
  - propose un bouton pour exporter le resultat final (code ou texte).

Architecture : cette interface est un simple client HTTP de l'API FastAPI
(api/main.py). Elle ne contient aucune logique multi-agents elle-meme -
principe de separation des responsabilites deja applique dans le projet
(cf. section 4.1 du rapport de mi-parcours, inversion de dependances).
"""
import time

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_URL = "http://localhost:8000"
API_KEY = "dev-local-key"          # meme cle que dans .env / Swagger
POLL_INTERVAL_SECONDS = 1.0        # frequence d'interrogation de l'API

AVATARS = {
    "user": "🧑",
    "Agent_Orchestrateur": "🧭",
    "Agent_Codeur": "💻",
    "Agent_Reviseur": "🔍",
    "Agent_Critique": "🛡️",
}


def avatar_pour(source: str) -> str:
    """Retourne un emoji representatif de l'agent, ou un robot par defaut."""
    return AVATARS.get(source, "🤖")


st.set_page_config(page_title="Smartovate Multi-Agent", page_icon="🤖", layout="centered")

# ---------------------------------------------------------------------------
# Etat de session : ce qui doit survivre entre deux interactions Streamlit
# (Streamlit re-execute tout le script a chaque interaction, sans ceci
#  on perdrait la tache en cours a chaque clic)
# ---------------------------------------------------------------------------
if "task_id" not in st.session_state:
    st.session_state.task_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "reponse_finale" not in st.session_state:
    st.session_state.reponse_finale = None
if "statut" not in st.session_state:
    st.session_state.statut = None

# ---------------------------------------------------------------------------
# En-tete
# ---------------------------------------------------------------------------
st.title("🤖 Smartovate Multi-Agent System")
st.caption("PoC AutoGen v0.4 + Azure OpenAI — stage Haitham Dhaimi (2026)")

# ---------------------------------------------------------------------------
# Formulaire de soumission
# ---------------------------------------------------------------------------
with st.form("formulaire_tache"):
    tache = st.text_area(
        "Decrivez votre tache",
        placeholder="Ex : Ecris une fonction Python qui calcule la suite de Fibonacci",
        height=100,
    )
    soumis = st.form_submit_button("🚀 Soumettre au systeme multi-agents")

if soumis:
    if len(tache.strip()) < 5:
        st.error("La tache doit contenir au moins 5 caracteres.")
    else:
        # Reinitialise l'etat pour une nouvelle tache
        st.session_state.messages = []
        st.session_state.reponse_finale = None
        st.session_state.statut = None

        try:
            r = requests.post(
                f"{API_URL}/tasks",
                headers={"x-api-key": API_KEY},
                json={"task": tache},
                timeout=10,
            )
            r.raise_for_status()
            st.session_state.task_id = r.json()["task_id"]
        except requests.exceptions.ConnectionError:
            st.error("Impossible de contacter l'API. Le serveur uvicorn est-il lance ?")
            st.session_state.task_id = None
        except requests.exceptions.HTTPError as exc:
            st.error(f"Erreur API : {exc}")
            st.session_state.task_id = None

# ---------------------------------------------------------------------------
# Suivi en temps reel de la tache en cours (coeur de l'US 3.2)
# ---------------------------------------------------------------------------
if st.session_state.task_id and st.session_state.statut not in ("TERMINE", "ERREUR"):
    st.divider()
    st.subheader("💬 Echanges entre agents")

    zone_conversation = st.empty()
    zone_statut = st.empty()

    while True:
        r = requests.get(
            f"{API_URL}/tasks/{st.session_state.task_id}",
            headers={"x-api-key": API_KEY},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()

        st.session_state.statut = data["statut"]
        st.session_state.messages = data.get("messages", [])
        st.session_state.reponse_finale = data.get("reponse")

        # Reaffiche la conversation complete a chaque tour de boucle :
        # c'est cette reecriture repetee de zone_conversation qui cree
        # l'effet "temps reel" cote navigateur.
        with zone_conversation.container():
            for m in st.session_state.messages:
                with st.chat_message(m["source"], avatar=avatar_pour(m["source"])):
                    st.markdown(f"**{m['source']}**")
                    st.markdown(m["contenu"])

        if st.session_state.statut == "TERMINE":
            zone_statut.success("✅ Tache terminee.")
            break
        elif st.session_state.statut == "ERREUR":
            zone_statut.error(f"❌ Erreur : {st.session_state.reponse_finale}")
            break
        else:
            zone_statut.info(f"⏳ Statut : {st.session_state.statut}")
            time.sleep(POLL_INTERVAL_SECONDS)

# ---------------------------------------------------------------------------
# Resultat final + export (critere US 3.2 : "bouton pour exporter
# le resultat final, code ou texte")
# ---------------------------------------------------------------------------
if st.session_state.statut == "TERMINE" and st.session_state.reponse_finale:
    st.divider()
    st.subheader("📄 Resultat final")
    st.markdown(st.session_state.reponse_finale)

    st.download_button(
        label="⬇️ Exporter le resultat",
        data=st.session_state.reponse_finale,
        file_name=f"resultat_{st.session_state.task_id[:8]}.md",
        mime="text/markdown",
    )