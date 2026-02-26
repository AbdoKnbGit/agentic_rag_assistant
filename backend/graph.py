"""
graph.py — Pipeline Agentic RAG avec LangGraph
État : QueryState → chaque nœud enrichit l'état → réponse finale.

Nœuds :
  analyze → retrieve → [data_analysis?] → generate → critic → output
"""

from __future__ import annotations
from typing import TypedDict, Optional, List
import structlog
from langgraph.graph import StateGraph, END
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, SystemMessage
from typing import AsyncGenerator

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from backend.config import settings
from backend.retrieval_service.retriever import HybridRetrieverOptimized as HybridRetriever
from backend.data_agent_service.analyst import analyze_file, format_analysis_for_llm
from backend.critic_service.critic import node_critic
from backend.cache import cache_key, get_cached, set_cached, stream_cached


logger = structlog.get_logger()


# ── System Prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a highly intelligent document assistant. You analyze uploaded documents with precision and answer user questions based on their content.

CORE BEHAVIOR:
- Read every document chunk provided carefully and thoroughly
- Extract relevant information and synthesize a clear, complete answer
- Cite the source filename for each piece of information (e.g. "According to [filename]...")
- If the documents don't contain the answer, say so explicitly, then provide your own knowledge clearly marked as such
- Respond in the SAME LANGUAGE as the user's question

CONVERSATION STYLE:
- Be natural, clear, and conversational — like a knowledgeable colleague
- Give direct answers first, then elaborate if needed
- Use structured formatting (headers, bullet points, bold) when it helps clarity
- Never give superficial one-liner answers — provide real depth and insight
- When the user asks follow-up questions, reference the context of the conversation naturally

DOCUMENT ANALYSIS:
- When multiple documents are provided, compare and cross-reference them
- Identify key concepts, facts, numbers, and relationships
- If a question requires synthesis across documents, do it explicitly
- Pay attention to specific details — names, dates, numbers, definitions
"""

SYSTEM_PROMPT_REASONING = """You are a highly intelligent document assistant with deep reasoning capabilities. Think step by step through complex questions.

CORE BEHAVIOR:
- Read every document chunk provided carefully and thoroughly
- Think deeply before answering — consider multiple angles
- Extract relevant information and synthesize a clear, complete answer
- Cite the source filename for each piece of information
- If the documents don't contain the answer, say so explicitly, then provide your own knowledge clearly marked as such
- Respond in the SAME LANGUAGE as the user's question

REASONING APPROACH:
- Break complex questions into sub-questions
- Consider what the documents actually say vs what might be inferred
- Cross-reference information across documents
- Identify contradictions or gaps in the provided information
- Provide well-reasoned, thorough answers with evidence

CONVERSATION STYLE:
- Be natural, clear, and conversational
- Give direct answers first, then elaborate
- Use structured formatting when it helps clarity
- Never give superficial answers — provide real depth and insight
"""


# ── State ─────────────────────────────────────────────────────────────────────

class QueryState(TypedDict):
    # Input
    query: str
    source_filter: Optional[List[str]]
    data_file: Optional[str]
    chat_history: List[dict]
    reasoning: bool

    # Computed
    reformulated_query: str
    retrieved_docs: List[dict]
    data_analysis: Optional[str]
    answer: str
    critic_result: dict
    final_answer: str
    needs_clarification: bool


# ── LLM factory ───────────────────────────────────────────────────────────────

def get_llm(reasoning: bool = False) -> ChatNVIDIA:
    kwargs = dict(
        model=settings.llm_model,
        api_key=settings.nvidia_api_key,
        temperature=settings.llm_temperature,
        top_p=settings.llm_top_p,
        max_tokens=settings.llm_max_tokens,
    )
    if reasoning:
        kwargs["extra_body"] = {"chat_template_kwargs": {"thinking": True}}
    return ChatNVIDIA(**kwargs)


# ── Retry-wrapped LLM call ───────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=15),
    retry=retry_if_exception_type(Exception),
    before_sleep=lambda retry_state: logger.warning(
        "llm_retry",
        attempt=retry_state.attempt_number,
        error=str(retry_state.outcome.exception()) if retry_state.outcome else "unknown",
    ),
)
async def _call_llm(llm, messages):
    """Appel LLM avec retry automatique sur erreurs transitoires (async)."""
    return await llm.ainvoke(messages)


# ── Build messages ────────────────────────────────────────────────────────────

def _build_user_message(query: str, context: str, chat_history: list, data_analysis: str = None) -> str:
    """Build the user message with context, history, and query."""
    parts = []

    # Chat history for conversational context
    if chat_history:
        history_parts = []
        for msg in chat_history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prefix = "User" if role == "user" else "Assistant"
            history_parts.append(f"{prefix}: {content[:500]}")
        if history_parts:
            parts.append(f"CONVERSATION HISTORY:\n" + "\n".join(history_parts))

    # Document context
    if context:
        parts.append(f"DOCUMENTS:\n{context}")

    # Data analysis (CSV/Parquet)
    if data_analysis:
        parts.append(f"DATA ANALYSIS:\n{data_analysis}")

    # The actual question
    parts.append(f"QUESTION:\n{query}")

    return "\n\n---\n\n".join(parts)


# ── Nœuds ─────────────────────────────────────────────────────────────────────

async def node_analyze(state: QueryState) -> dict:
    """Analyse heuristique pure (async pour cohérence)."""
    query = state["query"]
    q = query.lower()

    reformulated = query
    if len(query.split()) < 4:
        reformulated = f"Explique en détail : {query}"
    elif any(w in q for w in ["c'est quoi", "qu'est-ce que", "définition de"]):
        reformulated = f"Définition et explication complète de : {query}"
    elif any(w in q for w in ["résumé", "resume", "synthèse"]):
        reformulated = f"Résumé complet et structuré de : {query}"

    logger.info("analyze_done", reformulated=reformulated[:80])

    return {
        "reformulated_query": reformulated,
        "needs_clarification": len(query.split()) < 3,
    }


async def node_retrieve(state: QueryState) -> dict:
    """Retrieval hybride BM25 + Qdrant (AWAIT corrigé)."""
    retriever = HybridRetriever()
    docs = await retriever.retrieve(
        query=state["reformulated_query"],
        top_k=10,
        source_filter=state.get("source_filter"),
    )
    return {"retrieved_docs": docs}


async def node_data_analysis(state: QueryState) -> dict:
    """Analyse le fichier de données si fourni (exécuté en thread)."""
    data_file = state.get("data_file")
    if not data_file:
        return {"data_analysis": None}
    try:
        # analyze_file est synchrone, on l'isole dans un thread pour ne pas bloquer l'event loop
        analysis = await asyncio.to_thread(analyze_file, data_file, topic=state["query"])
        formatted = format_analysis_for_llm(analysis)
        return {"data_analysis": formatted}
    except Exception as e:
        logger.error("data_analysis_error", error=str(e))
        return {"data_analysis": f"Erreur d'analyse : {e}"}


async def node_generate(state: QueryState) -> dict:
    """Génère la réponse avec le LLM (async)."""
    retriever = HybridRetriever()
    context = retriever.format_context(state["retrieved_docs"])

    reasoning = state.get("reasoning", False)
    system_prompt = SYSTEM_PROMPT_REASONING if reasoning else SYSTEM_PROMPT

    user_message = _build_user_message(
        query=state["query"],
        context=context,
        chat_history=state.get("chat_history", []),
        data_analysis=state.get("data_analysis"),
    )

    llm = get_llm(reasoning=reasoning)
    response = await _call_llm(llm, [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ])

    logger.info("generation_done", answer_length=len(response.content))
    return {"answer": response.content}


# ── Conditionals ──────────────────────────────────────────────────────────────

def route_data(state: QueryState) -> str:
    if state.get("data_file"):
        return "data_analysis"
    return "generate"


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(QueryState)

    graph.add_node("analyze", node_analyze)
    graph.add_node("retrieve", node_retrieve)
    graph.add_node("data_analysis", node_data_analysis)
    graph.add_node("generate", node_generate)
    graph.add_node("critic", node_critic)

    graph.set_entry_point("analyze")
    graph.add_edge("analyze", "retrieve")
    graph.add_conditional_edges("retrieve", route_data, {
        "data_analysis": "data_analysis",
        "generate": "generate",
    })
    graph.add_edge("data_analysis", "generate")
    graph.add_edge("generate", "critic")
    graph.add_edge("critic", END)

    return graph.compile()


# ── Public API ────────────────────────────────────────────────────────────────

compiled_graph = build_graph()


async def run_query(
    query: str,
    source_filter: Optional[str] = None,
    data_file: Optional[str] = None,
    chat_history: Optional[List[dict]] = None,
    reasoning: bool = False,
) -> dict:
    """Point d'entrée principal du pipeline RAG (Async)."""
    initial_state: QueryState = {
        "query": query,
        "source_filter": source_filter,
        "data_file": data_file,
        "chat_history": chat_history or [],
        "reasoning": reasoning,
        "reformulated_query": query,
        "retrieved_docs": [],
        "data_analysis": None,
        "answer": "",
        "critic_result": {},
        "final_answer": "",
        "needs_clarification": False,
    }

    result = await compiled_graph.ainvoke(initial_state)

    return {
        "query": query,
        "reformulated_query": result.get("reformulated_query", query),
        "answer": result["final_answer"],
        "sources": [d.get("source") for d in result["retrieved_docs"]],
        "critic": result["critic_result"],
    }


async def run_query_stream(
    query: str,
    source_filter: Optional[list[str]] = None,
    data_file: Optional[str] = None,
    chat_history: Optional[list[dict]] = None,
    reasoning: bool = False,
) -> AsyncGenerator[str, None]:
    import asyncio
    import json
    import uuid
    from pathlib import Path as PurePath

    reasoning_mode = reasoning
    interaction_id = str(uuid.uuid4())

    # ── Cache check
    c_key = cache_key(query)
    cached = get_cached(c_key)
    if cached is not None:
        logger.info("cache_hit_stream", query=query[:60])
        cached["interaction_id"] = interaction_id
        async for token in stream_cached(cached):
            yield token
        return

    # ── État initial
    state: QueryState = {
        "query": query,
        "source_filter": source_filter,
        "data_file": data_file,
        "chat_history": chat_history or [],
        "reasoning": reasoning_mode,
        "reformulated_query": query,
        "retrieved_docs": [],
        "data_analysis": None,
        "answer": "",
        "critic_result": {},
        "final_answer": "",
        "needs_clarification": False,
    }

    # ── Étape 1 : Analyze
    yield json.dumps({"type": "status", "step": "analyzing"})
    state.update(await node_analyze(state))

    # ── Étape 2 : Retrieve
    yield json.dumps({"type": "status", "step": "retrieving"})
    retriever = HybridRetriever()
    state["retrieved_docs"] = await retriever.retrieve(
        query=state["reformulated_query"],
        top_k=None,
        source_filter=source_filter,
    )

    # ── Étape 2b : Analyse du fichier (si fourni)
    if state.get("data_file"):
        yield json.dumps({"type": "status", "step": "analyzing_data"})
        analysis = await asyncio.to_thread(analyze_file, state["data_file"], topic=query)
        state["data_analysis"] = format_analysis_for_llm(analysis)

        csv_chunk = {
            "source": PurePath(state["data_file"]).name,
            "rrf_score": 1.0,
            "chunks": [state["data_analysis"]],
        }
        state["retrieved_docs"].append(csv_chunk)

    # ── Stream des chunks au frontend
    for i, doc in enumerate(state["retrieved_docs"], 1):
        source_name = doc.get("source", "inconnu")
        score = doc.get("rrf_score", 0)
        for j, chunk in enumerate(doc.get("chunks", []), 1):
            yield json.dumps({
                "type": "chunk",
                "document_index": i,
                "chunk_index": j,
                "text": chunk[:500],
                "source": source_name,
                "score": score,
            })

    # ── Étape 3 : Generate
    yield json.dumps({"type": "status", "step": "generating"})
    context = retriever.format_context(state["retrieved_docs"])

    system_prompt = SYSTEM_PROMPT_REASONING if reasoning_mode else SYSTEM_PROMPT

    user_message = _build_user_message(
        query=state["query"],
        context=context,
        chat_history=state.get("chat_history", []),
        data_analysis=state.get("data_analysis"),
    )

    # LLM
    llm = get_llm(reasoning=reasoning_mode)
    full_answer = ""
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]

    # ── Stream des tokens LLM
    for chunk in llm.stream(messages):
        token = chunk.content
        if token:
            full_answer += token
            yield json.dumps({"type": "token", "data": token})

    # ── Étape 4 : Critic
    state["answer"] = full_answer
    critic_state = await asyncio.to_thread(node_critic, state)
    critic_result = critic_state.get("critic_result", {})

    # ── Cache store (non-blocking)
    try:
        cache_data = {
            "answer": full_answer,
            "chunks": [
                {
                    "type": "chunk",
                    "document_index": i,
                    "chunk_index": j,
                    "text": chunk[:500],
                    "source": doc.get("source", "inconnu"),
                    "score": doc.get("rrf_score", 0),
                }
                for i, doc in enumerate(state["retrieved_docs"], 1)
                for j, chunk in enumerate(doc.get("chunks", []), 1)
            ],
            "critic": critic_result,
        }
        set_cached(c_key, cache_data)
    except Exception as e:
        logger.warning("cache_store_error", error=str(e))

    # ── MongoDB interaction logging (non-blocking)
    try:
        from backend.mongodb import get_mongo_db
        from datetime import datetime, timezone
        import time as _time

        mongo_db = get_mongo_db()
        if mongo_db is not None:
            interaction_doc = {
                "session_id": interaction_id,
                "timestamp": datetime.now(timezone.utc),
                "query": query,
                "reformulated_query": state.get("reformulated_query", query),
                "answer": full_answer[:5000],
                "sources_used": [d.get("source", "") for d in state.get("retrieved_docs", [])],
                "response_time_ms": 0,
            }
            mongo_db.interactions.insert_one(interaction_doc)
            logger.info("interaction_logged", interaction_id=interaction_id)
    except Exception as e:
        logger.warning("interaction_log_error", error=str(e))

    yield json.dumps({
        "type": "done",
        "critic": critic_result,
        "interaction_id": interaction_id,
    })