/**
 * AdminDashboard.jsx — Admin analytics and fine-tuning dashboard
 * Displays satisfaction stats, top questions, document scores, and fine-tuning controls
 */
import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    BarChart3, TrendingUp, MessageSquare, Zap,
    RefreshCw, ArrowLeft, ThumbsUp, ThumbsDown,
    Activity, FileText, ChevronRight
} from 'lucide-react';
import {
    getAnalyticsStats, getAnalyticsSatisfaction,
    getTopQuestions, triggerFinetune, getFinetuneStatus,
    getFinetuneWeights,
} from '../api';

// ── Simple Bar component (no external chart library needed) ──────────────────

function SimpleBar({ value, max, color = 'indigo' }) {
    const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
    const colorMap = {
        indigo: 'from-indigo-500 to-violet-500',
        emerald: 'from-emerald-500 to-cyan-500',
        rose: 'from-rose-500 to-pink-500',
        amber: 'from-amber-500 to-orange-500',
    };
    return (
        <div className="h-2 rounded-full bg-[var(--color-bg-hover)] overflow-hidden">
            <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
                className={`h-full rounded-full bg-gradient-to-r ${colorMap[color] || colorMap.indigo}`}
            />
        </div>
    );
}

// ── Stat Card ────────────────────────────────────────────────────────────────

function StatCard({ icon: Icon, label, value, sub, color = 'indigo' }) {
    const colorMap = {
        indigo: 'from-indigo-500/20 to-violet-500/20 border-indigo-500/30 text-indigo-400',
        emerald: 'from-emerald-500/20 to-cyan-500/20 border-emerald-500/30 text-emerald-400',
        amber: 'from-amber-500/20 to-orange-500/20 border-amber-500/30 text-amber-400',
        rose: 'from-rose-500/20 to-pink-500/20 border-rose-500/30 text-rose-400',
    };
    return (
        <div className="glass-panel-solid rounded-xl p-4">
            <div className="flex items-center gap-3 mb-2">
                <div className={`w-9 h-9 rounded-lg flex items-center justify-center bg-gradient-to-br border ${colorMap[color]}`}>
                    <Icon size={16} />
                </div>
                <div>
                    <p className="text-[0.6rem] text-[var(--color-text-muted)] uppercase tracking-wider">{label}</p>
                    <p className="text-lg font-bold text-[var(--color-text-primary)]">{value}</p>
                </div>
            </div>
            {sub && <p className="text-[0.6rem] text-[var(--color-text-dim)] mt-1">{sub}</p>}
        </div>
    );
}

// ── Main Dashboard ──────────────────────────────────────────────────────────

export default function AdminDashboard({ onClose }) {
    const [stats, setStats] = useState(null);
    const [satisfaction, setSatisfaction] = useState(null);
    const [topQuestions, setTopQuestions] = useState(null);
    const [finetuneStatus, setFinetuneStatus] = useState(null);
    const [weights, setWeights] = useState(null);
    const [loading, setLoading] = useState(true);
    const [triggerLoading, setTriggerLoading] = useState(false);
    const [triggerResult, setTriggerResult] = useState(null);

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const [s, sat, tq, fs, w] = await Promise.allSettled([
                getAnalyticsStats(),
                getAnalyticsSatisfaction(),
                getTopQuestions(10),
                getFinetuneStatus(),
                getFinetuneWeights(),
            ]);
            if (s.status === 'fulfilled') setStats(s.value);
            if (sat.status === 'fulfilled') setSatisfaction(sat.value);
            if (tq.status === 'fulfilled') setTopQuestions(tq.value);
            if (fs.status === 'fulfilled') setFinetuneStatus(fs.value);
            if (w.status === 'fulfilled') setWeights(w.value);
        } catch { /* ignore */ }
        setLoading(false);
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    async function handleTrigger() {
        setTriggerLoading(true);
        setTriggerResult(null);
        try {
            const result = await triggerFinetune();
            setTriggerResult(result);
            loadData(); // Refresh
        } catch (err) {
            setTriggerResult({ status: 'error', detail: err.message });
        }
        setTriggerLoading(false);
    }

    const maxQ = topQuestions?.questions?.length > 0
        ? Math.max(...topQuestions.questions.map(q => q.count))
        : 1;

    return (
        <motion.div
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 40 }}
            className="fixed inset-0 z-50 bg-[var(--color-bg-primary)]/95 backdrop-blur-xl overflow-y-auto"
        >
            <div className="max-w-5xl mx-auto px-6 py-8">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-3">
                        <button
                            onClick={onClose}
                            className="w-9 h-9 rounded-lg flex items-center justify-center text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-glass-hover)] transition-all cursor-pointer"
                        >
                            <ArrowLeft size={18} />
                        </button>
                        <div>
                            <h1 className="text-xl font-bold text-[var(--color-text-primary)]">Admin Dashboard</h1>
                            <p className="text-[0.65rem] text-[var(--color-text-muted)]">Analytics & Adaptive Fine-tuning</p>
                        </div>
                    </div>
                    <button
                        onClick={loadData}
                        disabled={loading}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-glass-hover)] transition-all cursor-pointer"
                    >
                        <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
                        Refresh
                    </button>
                </div>

                {loading && !stats ? (
                    <div className="flex items-center justify-center py-20">
                        <RefreshCw size={24} className="animate-spin text-[var(--color-accent-indigo)]" />
                    </div>
                ) : (
                    <div className="space-y-6">
                        {/* Stats Grid */}
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                            <StatCard
                                icon={MessageSquare} label="Total Queries"
                                value={stats?.total_queries || 0}
                                sub={`${stats?.queries_today || 0} today`}
                                color="indigo"
                            />
                            <StatCard
                                icon={Activity} label="Avg Response"
                                value={`${stats?.avg_response_time_ms || 0}ms`}
                                color="amber"
                            />
                            <StatCard
                                icon={ThumbsUp} label="Satisfaction"
                                value={`${satisfaction?.satisfaction_rate || 0}%`}
                                sub={`${satisfaction?.positive || 0} 👍  ${satisfaction?.negative || 0} 👎`}
                                color="emerald"
                            />
                            <StatCard
                                icon={Zap} label="Fine-tune Level"
                                value={finetuneStatus?.available_level || 0}
                                sub={`${finetuneStatus?.total_feedbacks || 0} feedbacks`}
                                color="rose"
                            />
                        </div>

                        {/* Two-column layout */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            {/* Top Questions */}
                            <div className="glass-panel-solid rounded-xl p-5">
                                <h2 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4 flex items-center gap-2">
                                    <TrendingUp size={14} className="text-[var(--color-accent-indigo)]" />
                                    Top Questions
                                </h2>
                                <div className="space-y-3">
                                    {topQuestions?.questions?.length > 0 ? (
                                        topQuestions.questions.map((q, i) => (
                                            <div key={i}>
                                                <div className="flex items-center justify-between mb-1">
                                                    <span className="text-xs text-[var(--color-text-secondary)] truncate max-w-[80%]">
                                                        {q.query}
                                                    </span>
                                                    <span className="text-[0.6rem] text-[var(--color-text-muted)] shrink-0 ml-2">
                                                        {q.count}×
                                                    </span>
                                                </div>
                                                <SimpleBar value={q.count} max={maxQ} color="indigo" />
                                            </div>
                                        ))
                                    ) : (
                                        <p className="text-xs text-[var(--color-text-dim)] italic">No queries yet</p>
                                    )}
                                </div>
                            </div>

                            {/* RRF Weights */}
                            <div className="glass-panel-solid rounded-xl p-5">
                                <h2 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4 flex items-center gap-2">
                                    <BarChart3 size={14} className="text-[var(--color-accent-violet)]" />
                                    Document Weights (RRF)
                                </h2>
                                <div className="space-y-3">
                                    {weights?.weights && Object.keys(weights.weights).length > 0 ? (
                                        Object.entries(weights.weights).map(([source, data]) => (
                                            <div key={source} className="flex items-center justify-between">
                                                <div className="flex items-center gap-2 min-w-0">
                                                    <FileText size={12} className="text-[var(--color-text-dim)] shrink-0" />
                                                    <span className="text-xs text-[var(--color-text-secondary)] truncate">{source}</span>
                                                </div>
                                                <div className="flex items-center gap-2 shrink-0 ml-2">
                                                    <span className={`text-[0.6rem] px-1.5 py-0.5 rounded ${data.action === 'boosted' ? 'bg-emerald-500/10 text-emerald-400' :
                                                            data.action === 'reduced' ? 'bg-rose-500/10 text-rose-400' :
                                                                'bg-[var(--color-glass)] text-[var(--color-text-muted)]'
                                                        }`}>
                                                        {data.weight}×
                                                    </span>
                                                </div>
                                            </div>
                                        ))
                                    ) : (
                                        <p className="text-xs text-[var(--color-text-dim)] italic">
                                            No weights computed yet (need ≥10 feedbacks)
                                        </p>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Fine-tuning Controls */}
                        <div className="glass-panel-solid rounded-xl p-5">
                            <h2 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4 flex items-center gap-2">
                                <Zap size={14} className="text-[var(--color-accent-amber)]" />
                                Adaptive Fine-tuning
                            </h2>

                            <div className="flex items-start gap-4">
                                <div className="flex-1">
                                    <div className="flex items-center gap-4 mb-3">
                                        {[1, 2, 3].map(level => (
                                            <div key={level} className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs ${(finetuneStatus?.available_level || 0) >= level
                                                    ? 'bg-[var(--color-accent-emerald)]/10 text-[var(--color-accent-emerald)] border border-[var(--color-accent-emerald)]/20'
                                                    : 'bg-[var(--color-glass)] text-[var(--color-text-dim)] border border-[var(--color-border)]'
                                                }`}>
                                                <span className="font-bold">L{level}</span>
                                                <span className="hidden sm:inline">
                                                    {level === 1 ? 'Weights' : level === 2 ? 'Prompts' : 'Re-index'}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                    <p className="text-[0.65rem] text-[var(--color-text-muted)] mb-3">
                                        Level 1: ≥10 feedbacks · Level 2: ≥50 feedbacks · Level 3: ≥100 feedbacks
                                    </p>
                                </div>

                                <button
                                    onClick={handleTrigger}
                                    disabled={triggerLoading || (finetuneStatus?.available_level || 0) < 1}
                                    className="shrink-0 flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium
                                        bg-gradient-to-r from-indigo-500 to-violet-500 text-white
                                        hover:from-indigo-400 hover:to-violet-400
                                        disabled:opacity-40 disabled:cursor-not-allowed
                                        transition-all cursor-pointer shadow-lg shadow-indigo-500/20"
                                >
                                    {triggerLoading ? (
                                        <RefreshCw size={14} className="animate-spin" />
                                    ) : (
                                        <Zap size={14} />
                                    )}
                                    {triggerLoading ? 'Analyzing...' : 'Trigger Analysis'}
                                </button>
                            </div>

                            {/* Trigger Result */}
                            <AnimatePresence>
                                {triggerResult && (
                                    <motion.div
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0 }}
                                        className="mt-4 p-3 rounded-lg bg-[var(--color-bg-primary)] border border-[var(--color-border)] text-xs"
                                    >
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className={`w-2 h-2 rounded-full ${triggerResult.status === 'ok' ? 'bg-emerald-400' : 'bg-rose-400'
                                                }`} />
                                            <span className="font-medium text-[var(--color-text-primary)]">
                                                {triggerResult.status === 'ok' ? 'Analysis Complete' : 'Error'}
                                            </span>
                                        </div>
                                        {triggerResult.levels_completed && (
                                            <p className="text-[var(--color-text-muted)]">
                                                Levels completed: {triggerResult.levels_completed.join(', ') || 'none'}
                                            </p>
                                        )}
                                        {triggerResult.message && (
                                            <p className="text-[var(--color-text-muted)]">{triggerResult.message}</p>
                                        )}
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </div>
                )}
            </div>
        </motion.div>
    );
}
