/**
 * ChatInput.jsx — Workspace query input
 * Beautiful input with send button and keyboard shortcut
 */
import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Send, Loader2, Brain } from 'lucide-react';

export default function ChatInput({ onSend, isStreaming, reasoning, onReasoningToggle }) {
    const [text, setText] = useState('');
    const textareaRef = useRef(null);

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + 'px';
        }
    }, [text]);

    function handleSubmit() {
        const trimmed = text.trim();
        if (!trimmed || isStreaming) return;
        onSend(trimmed, reasoning);
        setText('');
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }
    }

    function handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    }

    return (
        <div className="shrink-0 px-4 sm:px-8 lg:px-16 py-4">
            <div className="w-full">
                <motion.div
                    className="glass-panel rounded-2xl flex items-end gap-2 px-4 py-3 focus-within:border-[var(--color-border-active)] transition-all duration-300"
                    whileFocus={{ boxShadow: '0 0 20px rgba(99, 102, 241, 0.08)' }}
                >
                    <button
                        onClick={onReasoningToggle}
                        disabled={isStreaming}
                        title={reasoning ? "Désactiver le raisonnement approfondi" : "Activer le raisonnement approfondi"}
                        className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 transition-all duration-300 cursor-pointer ${reasoning
                            ? 'bg-[var(--color-accent-indigo)]/20 text-[var(--color-accent-indigo)] shadow-inner'
                            : 'bg-[var(--color-bg-hover)] text-[var(--color-text-dim)] hover:text-[var(--color-text-secondary)]'
                            }`}
                    >
                        <Brain size={16} className={reasoning ? 'animate-pulse' : ''} />
                    </button>

                    <div className="flex-1">
                        <textarea
                            ref={textareaRef}
                            value={text}
                            onChange={e => setText(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Ask a question about your documents…"
                            disabled={isStreaming}
                            rows={1}
                            className="w-full bg-transparent text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-dim)] outline-none resize-none leading-relaxed min-h-[px]"
                        />
                    </div>
                    <button
                        onClick={handleSubmit}
                        disabled={isStreaming || !text.trim()}
                        className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 transition-all duration-300 cursor-pointer ${text.trim() && !isStreaming
                            ? 'bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 hover:scale-105'
                            : 'bg-[var(--color-bg-hover)] text-[var(--color-text-dim)]'
                            }`}
                    >
                        {isStreaming ? (
                            <motion.div
                                animate={{ rotate: 360 }}
                                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                            >
                                <Loader2 size={16} />
                            </motion.div>
                        ) : (
                            <Send size={15} />
                        )}
                    </button>
                </motion.div>
                <p className="text-center text-[0.55rem] text-[var(--color-text-dim)] mt-2">
                    Enter to send · Shift+Enter for new line
                </p>
            </div>
        </div>
    );
}
