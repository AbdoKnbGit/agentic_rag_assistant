"""
critic.py — Validation avancée des réponses RAG
"""
import structlog
from typing import List
logger = structlog.get_logger()


# ── Fonctions publiques attendues par graph.py ────────────────────────────────

def validate_response(answer: str, retrieved_docs: list, query: str) -> dict:
    """Validation heuristique rapide — pas de LLM pour ne pas ralentir."""
    score = 1.0
    issues: List[str] = []

    if len(answer) < 50:
        score -= 0.3
        issues.append("Réponse trop courte")

    if not retrieved_docs:
        score -= 0.2
        issues.append("Aucun document source récupéré")

    critic_result = {
        "confidence_score": round(max(0.0, min(score, 1.0)), 2),
        "issues": issues,
        "llm_evaluation": {},
    }

    logger.info("critic_ok", score=critic_result["confidence_score"])
    return critic_result


def add_critic_footer(answer: str, critic_result: dict) -> str:
    """Retourne la réponse telle quelle — le footer est géré côté frontend."""
    return answer


# ── Nœud LangGraph (usage interne graph.py) ──────────────────────────────────

def node_critic(state: dict) -> dict:
    answer = state.get("answer", "")
    docs = state.get("retrieved_docs", [])
    query = state.get("query", "")

    critic_result = validate_response(answer, docs, query)
    final = add_critic_footer(answer, critic_result)

    return {"critic_result": critic_result, "final_answer": final}