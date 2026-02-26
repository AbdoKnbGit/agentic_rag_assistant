"""
data_agent_service/analyst.py
Analyse automatique des fichiers CSV et Parquet avec interprétation pédagogique.
"""
import pandas as pd
import numpy as np
import structlog
from pathlib import Path
from typing import Optional

logger = structlog.get_logger()


def analyze_dataframe(df: pd.DataFrame, topic: Optional[str] = None) -> dict:
    """
    Analyse statistique complète d'un DataFrame.
    Retourne un dict structuré prêt pour le LLM.
    """
    report = {}

    # ── Shape ──────────────────────────────────────────────────────────────
    report["shape"] = {"rows": len(df), "columns": len(df.columns)}
    report["columns"] = list(df.columns)
    report["dtypes"] = df.dtypes.astype(str).to_dict()

    # ── Valeurs manquantes ─────────────────────────────────────────────────
    missing = df.isnull().sum()
    report["missing_values"] = {
        col: int(count)
        for col, count in missing.items()
        if count > 0
    }

    # ── Stats numériques ───────────────────────────────────────────────────
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if numeric_cols:
        desc = df[numeric_cols].describe().round(4)
        report["numeric_stats"] = desc.to_dict()

        # Corrélations (si 2+ colonnes numériques)
        if len(numeric_cols) >= 2:
            corr = df[numeric_cols].corr().round(3)
            # Garder seulement les corrélations fortes (|r| > 0.5)
            strong_corr = {}
            for col1 in corr.columns:
                for col2 in corr.columns:
                    if col1 < col2:
                        val = corr.loc[col1, col2]
                        if abs(val) > 0.5:
                            strong_corr[f"{col1} ↔ {col2}"] = round(float(val), 3)
            report["strong_correlations"] = strong_corr

    # ── Stats catégorielles ────────────────────────────────────────────────
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    if cat_cols:
        report["categorical_stats"] = {
            col: {
                "unique_values": int(df[col].nunique()),
                "top_5": df[col].value_counts().head(5).to_dict(),
            }
            for col in cat_cols
        }

    # ── Insights automatiques ──────────────────────────────────────────────
    insights = []

    # Colonnes avec beaucoup de valeurs manquantes
    for col, count in report.get("missing_values", {}).items():
        pct = count / len(df) * 100
        if pct > 30:
            insights.append(f"⚠️ '{col}' a {pct:.0f}% de valeurs manquantes — à investiguer.")

    # Corrélations fortes
    for pair, val in report.get("strong_correlations", {}).items():
        direction = "positive" if val > 0 else "négative"
        insights.append(
            f"📈 Corrélation {direction} forte ({val}) entre {pair}."
        )

    # Distribution très asymétrique
    if numeric_cols:
        for col in numeric_cols:
            try:
                skew = float(df[col].skew())
                if abs(skew) > 2:
                    insights.append(
                        f"📊 '{col}' est très asymétrique (skewness={skew:.2f}) — "
                        f"penser à la transformation log."
                    )
            except Exception:
                pass

    report["insights"] = insights
    report["topic_context"] = topic or "Analyse générale"

    return report


def analyze_file(file_path: str, topic: Optional[str] = None) -> dict:
    """Charge et analyse un fichier CSV ou Parquet."""
    ext = Path(file_path).suffix.lower()

    if ext == ".csv":
        df = pd.read_csv(file_path)
    elif ext == ".parquet":
        df = pd.read_parquet(file_path)
    else:
        raise ValueError(f"Format non supporté pour l'analyse : {ext}")

    logger.info("data_analysis_start", file=file_path, shape=f"{len(df)}x{len(df.columns)}")
    result = analyze_dataframe(df, topic)
    result["source_file"] = file_path
    return result


def format_analysis_for_llm(analysis: dict) -> str:
    """Formate le rapport d'analyse en texte clair pour le LLM."""
    lines = [
        f"📊 ANALYSE DE DONNÉES — {analysis.get('source_file', 'fichier')}",
        f"Dimensions : {analysis['shape']['rows']} lignes × {analysis['shape']['columns']} colonnes",
        f"Colonnes : {', '.join(analysis['columns'])}",
        "",
    ]

    if analysis.get("missing_values"):
        lines.append("Valeurs manquantes :")
        for col, count in analysis["missing_values"].items():
            lines.append(f"  - {col}: {count}")
        lines.append("")

    if analysis.get("strong_correlations"):
        lines.append("Corrélations fortes :")
        for pair, val in analysis["strong_correlations"].items():
            lines.append(f"  - {pair}: {val}")
        lines.append("")

    if analysis.get("insights"):
        lines.append("Insights automatiques :")
        for insight in analysis["insights"]:
            lines.append(f"  {insight}")

    return "\n".join(lines)
