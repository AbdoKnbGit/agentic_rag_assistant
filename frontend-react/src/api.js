/**
 * api.js — Backend API communication layer (structured SSE)
 * Handles HTTP requests and parses structured JSON SSE events
 */

const API_BASE = import.meta.env.VITE_API_URL || '/api';

/**
 * Stream a RAG query via SSE — returns an async generator of structured events.
 * Event types: { type: 'status', step }, { type: 'chunks', data }, { type: 'token', data }, { type: 'done', critic }
 */
export async function* streamQuery({ query, sourceFilter, chatHistory, reasoning }) {
    const payload = {
        query,
        source_filter: sourceFilter || null,
        chat_history: chatHistory || [],
        reasoning: reasoning || false,
    };

    const response = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
        },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API Error (${response.status}): ${errorText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const raw = line.slice(6);
                if (raw === '[DONE]') return;
                if (raw.startsWith('[ERROR]')) {
                    throw new Error(raw.replace('[ERROR]', '').trim());
                }

                // Try to parse as structured JSON event
                try {
                    const event = JSON.parse(raw);
                    yield event;
                } catch {
                    // Fallback: plain text token (backward compat)
                    yield { type: 'token', data: raw };
                }
            }
        }
    }
}

/**
 * Get indexed sources list.
 */
export async function getSources() {
    try {
        const r = await fetch(`${API_BASE}/ingest/sources`, { signal: AbortSignal.timeout(5000) });
        const data = await r.json();
        return data.sources || [];
    } catch {
        return [];
    }
}

/**
 * Upload a file for ingestion.
 */
export async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const r = await fetch(`${API_BASE}/ingest/upload`, {
        method: 'POST',
        body: formData,
    });

    if (!r.ok) {
        const errorText = await r.text();
        throw new Error(errorText);
    }

    return await r.json();
}

/**
 * Delete a source from the index.
 */
export async function deleteSource(sourcePath) {
    const r = await fetch(`${API_BASE}/ingest/source`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_path: sourcePath }),
    });

    if (!r.ok) throw new Error('Failed to delete source');
    return await r.json();
}

/**
 * Health check.
 */
export async function checkHealth() {
    try {
        const r = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
        return await r.json();
    } catch {
        return null;
    }
}

/**
 * Send user feedback (👍/👎).
 */
export async function sendFeedback({ interactionId, score, query, answer, sourcesUsed }) {
    const r = await fetch(`${API_BASE}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            interaction_id: interactionId,
            score,
            query,
            answer,
            sources_used: sourcesUsed || [],
        }),
    });

    if (!r.ok) throw new Error('Failed to send feedback');
    return await r.json();
}

/**
 * Analytics — general stats.
 */
export async function getAnalyticsStats() {
    const r = await fetch(`${API_BASE}/analytics/stats`, { signal: AbortSignal.timeout(5000) });
    return await r.json();
}

/**
 * Analytics — satisfaction rate.
 */
export async function getAnalyticsSatisfaction() {
    const r = await fetch(`${API_BASE}/analytics/satisfaction`, { signal: AbortSignal.timeout(5000) });
    return await r.json();
}

/**
 * Analytics — top questions.
 */
export async function getTopQuestions(limit = 10) {
    const r = await fetch(`${API_BASE}/analytics/top-questions?limit=${limit}`, { signal: AbortSignal.timeout(5000) });
    return await r.json();
}

/**
 * Admin — trigger fine-tuning analysis.
 */
export async function triggerFinetune() {
    const r = await fetch(`${API_BASE}/admin/finetune/trigger`, { method: 'POST' });
    return await r.json();
}

/**
 * Admin — get fine-tuning status.
 */
export async function getFinetuneStatus() {
    const r = await fetch(`${API_BASE}/admin/finetune/status`, { signal: AbortSignal.timeout(5000) });
    return await r.json();
}

/**
 * Admin — get current RRF weights.
 */
export async function getFinetuneWeights() {
    const r = await fetch(`${API_BASE}/admin/finetune/weights`, { signal: AbortSignal.timeout(5000) });
    return await r.json();
}
