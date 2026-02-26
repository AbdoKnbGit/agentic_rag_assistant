"""
frontend/streamlit_app.py — Interface principale Agentic RAG
Avec : conversation memory, streaming UX, et design amélioré.
"""
import streamlit as st
import requests
import json
from pathlib import Path

import os
BACKEND_URL = os.getenv("BACKEND_URL", "http://host.docker.internal:8000")
# Au début du fichier
st.write(f"🔍 BACKEND_URL = {BACKEND_URL}")
st.write(f"🔍 Test connexion: {requests.get(f'{BACKEND_URL}/health').json()}")
# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🎓 Agentic RAG — Assistant Pédagogique",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS Premium ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    * { font-family: 'Inter', sans-serif; }

    .main-header {
        font-size: 2.4rem; font-weight: 800;
        background: linear-gradient(135deg, #4361ee, #7209b7);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem; color: #6c757d; margin-bottom: 2rem;
        font-weight: 300;
    }
    .answer-box {
        background: linear-gradient(135deg, #f8f9fa, #e8f4f8);
        border-left: 4px solid #4361ee;
        padding: 1.5rem; border-radius: 12px; margin-top: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .source-tag {
        background: linear-gradient(135deg, #e8f4f8, #d0ebff);
        border-radius: 6px; padding: 3px 10px;
        font-size: 0.8rem; margin-right: 4px; color: #0077b6;
        display: inline-block; margin-bottom: 4px;
        border: 1px solid #b5d8e8;
    }
    .critic-ok {
        color: #2d6a4f; font-size: 0.85rem;
        background: #d8f3dc; padding: 8px 12px; border-radius: 8px;
        margin-top: 8px;
    }
    .critic-warn {
        color: #e63946; font-size: 0.85rem;
        background: #fce4e4; padding: 8px 12px; border-radius: 8px;
        margin-top: 8px;
    }
    .reformulated-query {
        font-size: 0.82rem; color: #6c757d; font-style: italic;
        background: #f0f0f0; padding: 6px 10px; border-radius: 6px;
        margin-top: 4px; margin-bottom: 8px;
    }
    .llm-eval {
        font-size: 0.82rem; color: #555;
        background: #f5f3ff; padding: 8px 12px; border-radius: 8px;
        margin-top: 4px; border: 1px solid #e0d7ff;
    }
    .stButton > button {
        background: linear-gradient(135deg, #4361ee, #3a56d4);
        color: white; border-radius: 10px; border: none;
        font-weight: 600; padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #3451d1, #2d45b8);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(67, 97, 238, 0.35);
    }
    .sidebar-section-title {
        font-size: 0.9rem; font-weight: 600; color: #333;
        text-transform: uppercase; letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Profil étudiant")

    student_level = st.selectbox(
        "Ton niveau",
        ["débutant", "intermédiaire", "avancé", "expert"],
        index=1,
        help="Adapte la complexité des explications"
    )

    student_goal = st.selectbox(
        "Ton objectif",
        ["comprendre", "s'entraîner", "réviser", "examen"],
        index=0,
        help="Adapte la structure de la réponse"
    )

    st.divider()
    st.markdown("## 📄 Documents indexés")

    @st.cache_data(ttl=10)
    def get_sources():
        try:
            r = requests.get(f"{BACKEND_URL}/ingest/sources", timeout=5)
            return r.json().get("sources", [])
        except Exception:
            return []

    sources = get_sources()
    if sources:
        for s in sources:
            st.markdown(f"<span class='source-tag'>📁 {Path(s).name}</span>", unsafe_allow_html=True)
        source_filter = st.selectbox(
            "Filtrer par document (optionnel)",
            ["Tous les documents"] + sources
        )
        source_filter = None if source_filter == "Tous les documents" else source_filter
    else:
        st.info("Aucun document indexé. Uploadez-en un ci-dessous.")
        source_filter = None

    st.divider()

    # ── Upload ────────────────────────────────────────────────────────────
    st.markdown("## 📤 Uploader un document")
    uploaded_file = st.file_uploader(
        "PDF, DOCX, CSV, Parquet",
        type=["pdf", "docx", "csv", "parquet", "txt"],
        label_visibility="collapsed"
    )

    if uploaded_file and st.button("📥 Indexer", use_container_width=True):
        with st.spinner("Indexation en cours..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                r = requests.post(f"{BACKEND_URL}/ingest/upload", files=files, timeout=60)
                if r.status_code == 200:
                    st.success(f"✅ {uploaded_file.name} indexé !")
                    st.cache_data.clear()
                else:
                    st.error(f"Erreur: {r.text}")
            except Exception as e:
                st.error(f"Backend inaccessible : {e}")

    st.divider()
    st.markdown("## 🔗 Liens utiles")
    st.markdown("- [📖 API Docs](http://localhost:8000/docs)")
    st.markdown("- [📊 Grafana](http://localhost:3000)")
    st.markdown("- [🔍 Qdrant UI](http://localhost:6333/dashboard)")


# ── Main ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-header">🎓 Assistant Pédagogique RAG</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Pose une question sur tes documents. Je m\'adapte à ton niveau et je me souviens du contexte.</div>', unsafe_allow_html=True)

# ── Chat history ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Input ─────────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Pose ta question ici... (ex: Explique la règle de dérivation en chaîne)"):
    # Affiche la question
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # ── Appel API ─────────────────────────────────────────────────────────
    with st.chat_message("assistant"):
        # Spinner pendant les étapes silencieuses (analyze + retrieve)
        spinner_placeholder = st.empty()
        spinner_placeholder.markdown("🔍 *Reformulation, recherche & génération...*")

        try:
            chat_history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[:-1]
            ]

            payload = {
                "query": prompt,
                "student_level": student_level,
                "student_goal": student_goal,
                "source_filter": source_filter,
                "chat_history": chat_history,
            }

            # ── Streaming SSE ──────────────────────────────────────────────
            answer = ""
            stream_placeholder = st.empty()

            with requests.post(
                f"{BACKEND_URL}/query",
                json=payload,
                stream=True,
                headers={"Accept": "text/event-stream"},
                timeout=180,
            ) as r:

                if r.status_code != 200:
                    # Erreur HTTP — lire le body normalement
                    spinner_placeholder.empty()
                    try:
                        error_detail = r.json().get("error", r.text)
                    except Exception:
                        error_detail = r.text
                    st.error(f"Erreur API ({r.status_code}): {error_detail}")

                else:
                    spinner_placeholder.empty()  # Retire le spinner dès que le stream commence

                    for line in r.iter_lines():
                        if not line:
                            continue

                        # Format SSE : b"data: <token>"
                        if line.startswith(b"data: "):
                            token = line[6:].decode("utf-8")

                            if token == "[DONE]":
                                break
                            if token.startswith("[ERROR]"):
                                st.error(token.replace("[ERROR]", "❌ Erreur backend :"))
                                break

                            answer += token
                            # Affichage live avec curseur clignotant
                            stream_placeholder.markdown(answer + "▌")

                    # Réponse finale sans curseur
                    stream_placeholder.markdown(answer)

                    # ── Métadonnées : on fait un 2e appel léger pour sources/critic ──
                    # (ou on les inclut dans le dernier chunk — voir note ci-dessous)
                    if answer:
                        st.session_state.messages.append({"role": "assistant", "content": answer})

        except requests.exceptions.ConnectionError:
            spinner_placeholder.empty()
            st.error("❌ Backend inaccessible. Lance `docker-compose up` ou `uvicorn backend.main:app`")
        except requests.exceptions.Timeout:
            spinner_placeholder.empty()
            st.error("⏱️ Timeout — la requête a pris trop de temps. Essaie une question plus simple.")
        except Exception as e:
            spinner_placeholder.empty()
            st.error(f"Erreur inattendue : {e}")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption(f"🤖 Modèle : `Ollama (Mistral)`")
with col2:
    st.caption(f"🎓 Niveau : `{student_level}` | Objectif : `{student_goal}`")
with col3:
    if st.button("🗑️ Effacer la conversation"):
        st.session_state.messages = []
        st.rerun()