"""
frontend/admin_panel/admin.py — Panneau d'administration
Monitoring des documents, métriques, gestion de l'index.
"""
import streamlit as st
import requests
import json
from pathlib import Path
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="🛠 Admin — Agentic RAG",
    page_icon="🛠",
    layout="wide",
)

st.title("🛠 Panneau d'Administration")
st.divider()

# ── Health ────────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=3)
        if r.status_code == 200:
            data = r.json()
            st.metric("✅ Backend", "En ligne", delta=data.get("model", ""))
        else:
            st.metric("❌ Backend", "Hors ligne")
    except Exception:
        st.metric("❌ Backend", "Inaccessible")

with col2:
    try:
        r = requests.get(f"{BACKEND_URL}/ingest/sources", timeout=3)
        count = r.json().get("count", 0)
        st.metric("📄 Documents indexés", count)
    except Exception:
        st.metric("📄 Documents indexés", "N/A")

with col3:
    st.metric("📊 Grafana", "localhost:3000", delta="monitoring")

st.divider()

# ── Documents indexés ─────────────────────────────────────────────────────────
st.subheader("📄 Documents dans l'index")

try:
    r = requests.get(f"{BACKEND_URL}/ingest/sources", timeout=5)
    sources = r.json().get("sources", [])

    if sources:
        for source in sources:
            col_name, col_delete = st.columns([4, 1])
            with col_name:
                st.markdown(f"📁 `{Path(source).name}` — `{source}`")
            with col_delete:
                if st.button("🗑️ Supprimer", key=f"del_{source}"):
                    del_r = requests.delete(
                        f"{BACKEND_URL}/ingest/source",
                        json={"source_path": source},
                        timeout=10
                    )
                    if del_r.status_code == 200:
                        st.success(f"Supprimé : {source}")
                        st.rerun()
    else:
        st.info("Aucun document indexé.")
except Exception as e:
    st.error(f"Erreur : {e}")

st.divider()

# ── Test de recherche ─────────────────────────────────────────────────────────
st.subheader("🔍 Tester la recherche")

test_query = st.text_input("Query de test", placeholder="calcul intégral")
top_k = st.slider("Top K", 1, 20, 6)

if st.button("🔎 Lancer la recherche") and test_query:
    try:
        r = requests.post(
            f"{BACKEND_URL}/retrieve/search",
            json={"query": test_query, "top_k": top_k},
            timeout=15,
        )
        data = r.json()
        st.markdown(f"**{data['count']} résultats trouvés**")
        for i, doc in enumerate(data.get("results", []), 1):
            with st.expander(f"Doc {i} — Score RRF: {doc.get('rrf_score', '?')} — {Path(doc.get('source','?')).name}"):
                st.write(doc.get("text", "")[:500] + "...")
                st.json({k: v for k, v in doc.items() if k != "text"})
    except Exception as e:
        st.error(f"Erreur : {e}")

st.divider()

# ── Métriques Prometheus ──────────────────────────────────────────────────────
st.subheader("📊 Métriques en direct")

try:
    r = requests.get(f"{BACKEND_URL}/metrics", timeout=3)
    lines = [l for l in r.text.split("\n") if not l.startswith("#") and l.strip()]

    interesting = [
        ("rag_queries_total", "🔍 Requêtes RAG"),
        ("documents_ingested_total", "📥 Documents ingérés"),
        ("http_requests_total", "🌐 Requêtes HTTP"),
    ]

    cols = st.columns(len(interesting))
    for i, (metric_name, label) in enumerate(interesting):
        for line in lines:
            if line.startswith(metric_name + "{") or line.startswith(metric_name + " "):
                try:
                    value = float(line.split()[-1])
                    with cols[i]:
                        st.metric(label, int(value))
                    break
                except Exception:
                    pass

    with st.expander("Toutes les métriques Prometheus"):
        st.code(r.text[:3000])

except Exception:
    st.warning("Métriques indisponibles. Backend démarré ?")
