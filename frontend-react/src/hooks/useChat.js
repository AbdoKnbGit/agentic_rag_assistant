/**
 * useChat.js — Chat state management with structured SSE events
 * Manages messages, pipeline steps, retrieved chunks, and streaming state
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { streamQuery } from '../api';

const STORAGE_KEY = 'rag-chat-messages';

function loadMessages() {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        return saved ? JSON.parse(saved) : [];
    } catch {
        return [];
    }
}

function saveMessages(messages) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    } catch { /* ignore quota errors */ }
}
export function useChat() {
    const [messages, setMessages] = useState(loadMessages);
    const [isStreaming, setIsStreaming] = useState(false);
    const [error, setError] = useState(null);
    const [pipelineStep, setPipelineStep] = useState(null);
    const [retrievedChunks, setRetrievedChunks] = useState([]);
    const [criticResult, setCriticResult] = useState(null);
    const abortRef = useRef(null);

    // Persist messages
    useEffect(() => {
        saveMessages(messages);
    }, [messages]);

    const sendMessage = useCallback(async (query, { sourceFilter, reasoning }) => {
        setError(null);
        setPipelineStep(null);
        setRetrievedChunks([]);
        setCriticResult(null);

        // Add user message
        const userMsg = { role: 'user', content: query, timestamp: Date.now() };
        setMessages(prev => [...prev, userMsg]);

        // Prepare chat history
        const chatHistory = messages.map(m => ({ role: m.role, content: m.content }));

        // Start streaming
        setIsStreaming(true);
        const assistantMsg = { role: 'assistant', content: '', timestamp: Date.now(), chunks: [], critic: null, interactionId: null, queryContext: query };
        setMessages(prev => [...prev, assistantMsg]);

        try {
            let fullContent = '';
            let chunks = [];
            let critic = null;

            for await (const event of streamQuery({
                query,
                sourceFilter,
                chatHistory,
                reasoning,
            })) {
                switch (event.type) {
                    case 'status':
                        setPipelineStep(event.step);
                        break;

                    case 'chunks':
                        chunks = event.data || [];
                        setRetrievedChunks(chunks);
                        // Attach chunks to the message
                        setMessages(prev => {
                            const updated = [...prev];
                            updated[updated.length - 1] = {
                                ...updated[updated.length - 1],
                                chunks,
                            };
                            return updated;
                        });
                        break;

                    case 'token':
                        fullContent += event.data;
                        setMessages(prev => {
                            const updated = [...prev];
                            updated[updated.length - 1] = {
                                ...updated[updated.length - 1],
                                content: fullContent,
                            };
                            return updated;
                        });
                        break;

                    case 'done':
                        critic = event.critic || null;
                        setCriticResult(critic);
                        setMessages(prev => {
                            const updated = [...prev];
                            updated[updated.length - 1] = {
                                ...updated[updated.length - 1],
                                critic,
                                interactionId: event.interaction_id || null,
                            };
                            return updated;
                        });
                        setPipelineStep('done');
                        break;
                }
            }
        } catch (err) {
            setError(err.message);
            setMessages(prev => {
                const last = prev[prev.length - 1];
                if (last.role === 'assistant' && !last.content) {
                    return prev.slice(0, -1);
                }
                return prev;
            });
        } finally {
            setIsStreaming(false);
        }
    }, [messages]);

    const clearMessages = useCallback(() => {
        setMessages([]);
        setError(null);
        setPipelineStep(null);
        setRetrievedChunks([]);
        setCriticResult(null);
    }, []);

    return {
        messages,
        isStreaming,
        error,
        pipelineStep,
        retrievedChunks,
        criticResult,
        sendMessage,
        clearMessages,
    };
}
