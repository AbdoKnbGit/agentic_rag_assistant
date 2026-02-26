/**
 * FeedbackButtons.jsx — 👍/👎 feedback buttons for assistant messages
 * Sends user feedback to backend, disables after vote with confirmation animation
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ThumbsUp, ThumbsDown, Check } from 'lucide-react';
import { sendFeedback } from '../api';

export default function FeedbackButtons({ interactionId, query, answer, sources }) {
    const [voted, setVoted] = useState(null); // 'up' | 'down' | null
    const [loading, setLoading] = useState(false);

    if (!interactionId) return null;

    async function handleVote(score) {
        if (voted || loading) return;
        setLoading(true);

        try {
            await sendFeedback({
                interactionId,
                score,
                query: query || '',
                answer: answer || '',
                sourcesUsed: sources || [],
            });
            setVoted(score === 1 ? 'up' : 'down');
        } catch (err) {
            console.error('Feedback error:', err);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="flex items-center gap-1.5 mt-2">
            <AnimatePresence mode="wait">
                {voted ? (
                    <motion.div
                        key="confirmed"
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[var(--color-accent-emerald)]/10 border border-[var(--color-accent-emerald)]/20"
                    >
                        <Check size={12} className="text-[var(--color-accent-emerald)]" />
                        <span className="text-[0.6rem] text-[var(--color-accent-emerald)] font-medium">
                            {voted === 'up' ? 'Helpful' : 'Noted'}
                        </span>
                    </motion.div>
                ) : (
                    <motion.div
                        key="buttons"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        className="flex items-center gap-1"
                    >
                        <button
                            onClick={() => handleVote(1)}
                            disabled={loading}
                            className="group w-7 h-7 rounded-lg flex items-center justify-center
                                text-[var(--color-text-dim)] hover:text-[var(--color-accent-emerald)]
                                hover:bg-[var(--color-accent-emerald)]/10
                                border border-transparent hover:border-[var(--color-accent-emerald)]/20
                                transition-all duration-200 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                            title="Helpful"
                        >
                            <ThumbsUp size={13} className="transition-transform group-hover:scale-110" />
                        </button>
                        <button
                            onClick={() => handleVote(-1)}
                            disabled={loading}
                            className="group w-7 h-7 rounded-lg flex items-center justify-center
                                text-[var(--color-text-dim)] hover:text-[var(--color-accent-rose)]
                                hover:bg-[var(--color-accent-rose)]/10
                                border border-transparent hover:border-[var(--color-accent-rose)]/20
                                transition-all duration-200 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                            title="Not helpful"
                        >
                            <ThumbsDown size={13} className="transition-transform group-hover:scale-110" />
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
