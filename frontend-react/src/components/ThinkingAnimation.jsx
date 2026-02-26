/**
 * ThinkingAnimation.jsx — Intelligent thinking/reasoning animation
 * Shows contextual messages based on current pipeline step
 */
import { motion } from 'framer-motion';
import { Brain, Search, Database, Cpu, Sparkles } from 'lucide-react';

const STEP_INFO = {
    analyzing: {
        icon: Search,
        label: 'Analyzing question…',
        sublabel: 'Reformulation and intent detection',
        color: 'var(--color-accent-cyan)',
    },
    retrieving: {
        icon: Database,
        label: 'Searching documents…',
        sublabel: 'Embedding → Vector Search → BM25 → RRF Fusion',
        color: 'var(--color-accent-indigo)',
    },
    analyzing_data: {
        icon: Brain,
        label: 'Analyzing data…',
        sublabel: 'Statistical file processing',
        color: 'var(--color-accent-amber)',
    },
    generating: {
        icon: Cpu,
        label: 'Assistant reasoning…',
        sublabel: 'Generating educational response',
        color: 'var(--color-accent-violet)',
    },
};

export default function ThinkingAnimation({ step }) {
    const info = STEP_INFO[step] || STEP_INFO.generating;
    const Icon = info.icon;

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex items-center gap-3 px-5 py-3"
        >
            {/* Animated icon */}
            <motion.div
                className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                style={{
                    background: `${info.color}15`,
                    border: `1px solid ${info.color}30`,
                }}
                animate={{
                    boxShadow: [
                        `0 0 0px ${info.color}00`,
                        `0 0 20px ${info.color}30`,
                        `0 0 0px ${info.color}00`,
                    ],
                }}
                transition={{ duration: 2, repeat: Infinity }}
            >
                <Icon size={18} style={{ color: info.color }} />
            </motion.div>

            {/* Labels */}
            <div className="flex-1 min-w-0">
                <motion.p
                    className="text-sm font-medium"
                    style={{ color: info.color }}
                    key={step}
                    initial={{ opacity: 0, x: -5 }}
                    animate={{ opacity: 1, x: 0 }}
                >
                    {info.label}
                </motion.p>
                <p className="text-[0.65rem] text-[var(--color-text-muted)] truncate">
                    {info.sublabel}
                </p>
            </div>

            {/* Thinking dots */}
            <div className="flex gap-1">
                {[0, 1, 2].map(i => (
                    <motion.div
                        key={i}
                        className="w-1.5 h-1.5 rounded-full"
                        style={{ background: info.color }}
                        animate={{
                            opacity: [0.3, 1, 0.3],
                            scale: [0.8, 1.2, 0.8],
                        }}
                        transition={{
                            duration: 1.2,
                            repeat: Infinity,
                            delay: i * 0.2,
                        }}
                    />
                ))}
            </div>
        </motion.div>
    );
}
