/**
 * PipelineViz.jsx — RAG pipeline visualization
 * Shows: Analyze → Retrieve → Generate → Done with live status
 */
import { motion } from 'framer-motion';
import { Search, Database, Cpu, CheckCircle, Sparkles } from 'lucide-react';

const STEPS = [
    { key: 'analyzing', label: 'Analyze', icon: Search, color: 'var(--color-accent-cyan)' },
    { key: 'retrieving', label: 'Retrieve', icon: Database, color: 'var(--color-accent-indigo)' },
    { key: 'generating', label: 'Generate', icon: Cpu, color: 'var(--color-accent-violet)' },
    { key: 'done', label: 'Done', icon: CheckCircle, color: 'var(--color-accent-emerald)' },
];

function getStepIndex(step) {
    return STEPS.findIndex(s => s.key === step);
}

export default function PipelineViz({ currentStep }) {
    const activeIdx = getStepIndex(currentStep);

    return (
        <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-1 px-4 py-3"
        >
            {STEPS.map((step, i) => {
                const Icon = step.icon;
                const isActive = i === activeIdx;
                const isPast = i < activeIdx;
                const isFuture = i > activeIdx;

                return (
                    <div key={step.key} className="flex items-center gap-1 flex-1 last:flex-none">
                        {/* Step dot + icon */}
                        <motion.div
                            className="flex items-center gap-2 shrink-0"
                            animate={{
                                scale: isActive ? 1.05 : 1,
                            }}
                            transition={{ type: 'spring', stiffness: 300 }}
                        >
                            <div
                                className="relative flex items-center justify-center w-8 h-8 rounded-lg transition-all duration-500"
                                style={{
                                    background: isActive || isPast
                                        ? `${step.color}20`
                                        : 'var(--color-bg-hover)',
                                    border: `1px solid ${isActive || isPast ? `${step.color}40` : 'var(--color-border)'}`,
                                }}
                            >
                                <Icon
                                    size={14}
                                    style={{
                                        color: isActive || isPast ? step.color : 'var(--color-text-dim)',
                                        transition: 'color 0.4s',
                                    }}
                                />
                                {isActive && (
                                    <motion.div
                                        className="absolute inset-0 rounded-lg"
                                        style={{
                                            border: `1px solid ${step.color}`,
                                            boxShadow: `0 0 12px ${step.color}40`,
                                        }}
                                        animate={{ opacity: [0.5, 1, 0.5] }}
                                        transition={{ duration: 2, repeat: Infinity }}
                                    />
                                )}
                            </div>
                            <span
                                className="text-[0.65rem] font-medium tracking-wide uppercase hidden sm:block"
                                style={{
                                    color: isActive ? step.color : isPast ? 'var(--color-text-secondary)' : 'var(--color-text-dim)',
                                    transition: 'color 0.4s',
                                }}
                            >
                                {step.label}
                            </span>
                        </motion.div>

                        {/* Connector line */}
                        {i < STEPS.length - 1 && (
                            <div className="flex-1 mx-1">
                                <div
                                    className="h-[2px] rounded-full transition-all duration-700"
                                    style={{
                                        background: isPast
                                            ? `linear-gradient(90deg, ${STEPS[i].color}, ${STEPS[i + 1].color})`
                                            : 'var(--color-border)',
                                    }}
                                />
                            </div>
                        )}
                    </div>
                );
            })}

            {/* Sparkle animation when active */}
            {currentStep && currentStep !== 'done' && (
                <motion.div
                    className="ml-2"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
                >
                    <Sparkles size={14} style={{ color: 'var(--color-accent-amber)' }} />
                </motion.div>
            )}
        </motion.div>
    );
}
