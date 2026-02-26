/**
 * TypingIndicator.jsx — Animated bouncing dots for streaming state
 */
import { Sparkles } from 'lucide-react';

export default function TypingIndicator() {
    return (
        <div className="animate-fadeInUp flex gap-4 px-4 py-5 sm:px-6 lg:px-8 max-w-4xl mx-auto w-full">
            {/* Avatar */}
            <div className="shrink-0 w-9 h-9 rounded-xl flex items-center justify-center mt-0.5 bg-gradient-to-br from-cyan-500 to-indigo-600 shadow-lg shadow-cyan-500/20 animate-pulse-glow">
                <Sparkles size={17} className="text-white" />
            </div>

            {/* Dots */}
            <div className="flex-1">
                <div className="text-xs font-semibold mb-1.5 tracking-wide uppercase text-cyan-400">
                    Assistant RAG
                </div>
                <div className="bg-[var(--color-bg-assistant-msg)] border border-[var(--color-border)] rounded-2xl px-5 py-4 inline-flex items-center gap-1.5">
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                    <span className="ml-3 text-sm text-[var(--color-text-muted)]">Réflexion en cours…</span>
                </div>
            </div>
        </div>
    );
}
