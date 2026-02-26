import { motion } from "framer-motion";
import {
    Brain,
    BookOpen,
    Sparkles,
    Code2,
    FlaskConical,
    MessageCircle,
} from "lucide-react";

const SUGGESTIONS = [
    {
        icon: BookOpen,
        label: "Explain a concept",
        query: "Explain the main concept of my document",
        color: "#6366f1",
    },
    {
        icon: FlaskConical,
        label: "Summarize a course",
        query: "Create a structured summary of my documents",
        color: "#06b6d4",
    },
    {
        icon: Code2,
        label: "Practical exercises",
        query: "Generate practical exercises based on my documents",
        color: "#8b5cf6",
    },
    {
        icon: MessageCircle,
        label: "Prepare for an exam",
        query: "Help me prepare for an exam on my documents' content",
        color: "#10b981",
    },
];

export default function WelcomeScreen({ onSendSuggestion }) {
    return (
        <div className="w-full h-full flex items-center justify-center px-6 py-10">
            {/* CENTER CONTAINER */}
            <div className="w-full max-w-3xl text-center">

                {/* LOGO */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.85 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ type: "spring", stiffness: 180 }}
                    className="relative mb-8 flex justify-center"
                >
                    <div className="w-20 h-20 rounded-3xl bg-[var(--color-glass)] border border-[var(--color-glass-border)] flex items-center justify-center shadow-lg backdrop-blur-xl">
                        <Brain size={34} className="text-[var(--color-accent-indigo)]" />
                    </div>

                    <motion.div
                        className="absolute -top-1 -right-1"
                        animate={{ y: [0, -4, 0], opacity: [0.5, 1, 0.5] }}
                        transition={{ duration: 3, repeat: Infinity }}
                    >
                        <Sparkles size={16} className="text-amber-400" />
                    </motion.div>
                </motion.div>

                {/* SUGGESTIONS */}
                <motion.div
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="grid grid-cols-1 sm:grid-cols-2 gap-3"
                >
                    {SUGGESTIONS.map((s, i) => {
                        const Icon = s.icon;

                        return (
                            <button
                                key={i}
                                onClick={() => onSendSuggestion(s.query)}
                                className="group text-left rounded-xl p-4 transition-all border border-[var(--color-border)] bg-[var(--color-glass)] hover:bg-[var(--color-glass-hover)] backdrop-blur-xl"
                            >
                                <div className="flex items-center gap-3">
                                    <div
                                        className="w-9 h-9 rounded-lg flex items-center justify-center"
                                        style={{
                                            background: `${s.color}15`,
                                            border: `1px solid ${s.color}30`,
                                        }}
                                    >
                                        <Icon size={16} style={{ color: s.color }} />
                                    </div>

                                    <div>
                                        <p
                                            className="text-xs font-semibold"
                                            style={{ color: s.color }}
                                        >
                                            {s.label}
                                        </p>

                                        <p className="text-[11px] text-[var(--color-text-muted)] line-clamp-1">
                                            {s.query}
                                        </p>
                                    </div>
                                </div>
                            </button>
                        );
                    })}
                </motion.div>

            </div>
        </div>
    );
}