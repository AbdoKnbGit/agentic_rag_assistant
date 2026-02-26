/**
 * KnowledgeSidebar.jsx — Left sidebar
 * Shows: knowledge sources, profile settings, session history
 */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Database, FileText, Upload, Trash2, ChevronRight,
    Sparkles, PanelLeftClose, Brain,
} from 'lucide-react';
import { getSources, uploadFile, deleteSource } from '../api';

export default function KnowledgeSidebar({ selectedSources, onSourceToggle, isOpen, onToggle }) {
    const [sources, setSources] = useState([]);
    const [uploading, setUploading] = useState(false);
    const [expandedSection, setExpandedSection] = useState('sources');

    useEffect(() => {
        fetchSources();
        const interval = setInterval(fetchSources, 15000);
        return () => clearInterval(interval);
    }, []);

    async function fetchSources() {
        const s = await getSources();
        setSources(s);
    }

    async function handleUpload(e) {
        const file = e.target.files?.[0];
        if (!file) return;
        setUploading(true);
        try {
            await uploadFile(file);
            await fetchSources();
        } catch (err) {
            console.error(err);
        }
        setUploading(false);
        e.target.value = '';
    }

    async function handleDelete(src) {
        try {
            await deleteSource(src);
            await fetchSources();
        } catch (err) {
            console.error(err);
        }
    }

    function getFilename(path) {
        return path.split('/').pop().split('\\').pop();
    }

    const Section = ({ id, title, icon: Icon, children }) => {
        const isExpanded = expandedSection === id;
        return (
            <div className="border-b border-[var(--color-border)] last:border-0">
                <button
                    onClick={() => setExpandedSection(isExpanded ? null : id)}
                    className="w-full flex items-center gap-2.5 px-4 py-3 hover:bg-[var(--color-glass-hover)] transition-colors cursor-pointer"
                >
                    <Icon size={14} className="text-[var(--color-text-muted)] shrink-0" />
                    <span className="text-xs font-medium text-[var(--color-text-secondary)] flex-1 text-left">{title}</span>
                    <motion.div animate={{ rotate: isExpanded ? 90 : 0 }} transition={{ duration: 0.2 }}>
                        <ChevronRight size={12} className="text-[var(--color-text-dim)]" />
                    </motion.div>
                </button>
                <AnimatePresence>
                    {isExpanded && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                        >
                            <div className="px-4 pb-3">
                                {children}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        );
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.aside
                    initial={{ width: 0, opacity: 0 }}
                    animate={{ width: 280, opacity: 1 }}
                    exit={{ width: 0, opacity: 0 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                    className="h-full glass-panel-solid flex flex-col relative z-20 overflow-hidden shrink-0"
                >
                    {/* Header */}
                    <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
                        <div className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                                <Brain size={15} className="text-white" />
                            </div>
                            <div>
                                <h1 className="text-sm font-bold text-[var(--color-text-primary)] leading-tight">RAG Studio</h1>
                                <p className="text-[0.55rem] text-[var(--color-text-muted)] uppercase tracking-widest">Workspace</p>
                            </div>
                        </div>
                        <button
                            onClick={onToggle}
                            className="w-7 h-7 rounded-lg flex items-center justify-center text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-glass-hover)] transition-all cursor-pointer"
                        >
                            <PanelLeftClose size={15} />
                        </button>
                    </div>

                    {/* Scrollable content */}
                    <div className="flex-1 overflow-y-auto">
                        {/* Knowledge Sources */}
                        <Section id="sources" title="Knowledge Sources" icon={Database}>
                            <div className="space-y-1.5 mb-3">
                                {sources.length === 0 ? (
                                    <p className="text-[0.65rem] text-[var(--color-text-dim)] text-center py-2">
                                        No indexed documents
                                    </p>
                                ) : (
                                    sources.map((src, i) => {
                                        const isSelected = selectedSources.includes(src);
                                        return (
                                            <motion.div
                                                key={src}
                                                initial={{ opacity: 0, x: -10 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                transition={{ delay: i * 0.05 }}
                                                onClick={() => onSourceToggle(src)}
                                                className={`group flex items-center gap-2 px-2.5 py-2 rounded-lg transition-all cursor-pointer ${isSelected
                                                    ? 'bg-[var(--color-accent-indigo)]/10 border border-[var(--color-accent-indigo)]/20 shadow-sm shadow-indigo-500/5'
                                                    : 'hover:bg-[var(--color-glass-hover)] border border-transparent'
                                                    }`}
                                            >
                                                <div className={`w-3.5 h-3.5 rounded border flex items-center justify-center transition-all ${isSelected
                                                    ? 'bg-[var(--color-accent-indigo)] border-[var(--color-accent-indigo)]'
                                                    : 'border-[var(--color-text-dim)]'
                                                    }`}>
                                                    {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                                                </div>
                                                <FileText size={12} className={isSelected ? 'text-[var(--color-accent-indigo)]' : 'text-[var(--color-text-muted)]'} />
                                                <span className={`text-[0.65rem] flex-1 truncate transition-colors ${isSelected ? 'text-[var(--color-text-primary)] font-medium' : 'text-[var(--color-text-secondary)]'
                                                    }`}>
                                                    {getFilename(src)}
                                                </span>
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); handleDelete(src); }}
                                                    className="opacity-0 group-hover:opacity-100 text-[var(--color-text-dim)] hover:text-[var(--color-accent-rose)] transition-all cursor-pointer"
                                                >
                                                    <Trash2 size={11} />
                                                </button>
                                            </motion.div>
                                        );
                                    })
                                )}
                            </div>

                            {/* Upload */}
                            <label className={`flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-dashed border-[var(--color-border)] hover:border-[var(--color-accent-indigo)]/40 hover:bg-[var(--color-accent-indigo)]/5 transition-all cursor-pointer ${uploading ? 'opacity-50 pointer-events-none' : ''}`}>
                                <input type="file" className="hidden" accept=".pdf,.docx,.csv,.parquet,.txt" onChange={handleUpload} />
                                {uploading ? (
                                    <motion.div
                                        animate={{ rotate: 360 }}
                                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                    >
                                        <Sparkles size={12} className="text-[var(--color-accent-indigo)]" />
                                    </motion.div>
                                ) : (
                                    <Upload size={12} className="text-[var(--color-text-muted)]" />
                                )}
                                <span className="text-[0.65rem] text-[var(--color-text-muted)]">
                                    {uploading ? 'Indexing…' : 'Upload document'}
                                </span>
                            </label>
                        </Section>

                        {/* Agent Tools */}
                        <Section id="tools" title="Agent Tools" icon={Sparkles}>
                            <div className="space-y-1">
                                {[
                                    { label: 'Hybrid search', desc: 'BM25 + Vectorial', active: true },
                                    { label: 'RRF Fusion', desc: 'Multi-source reranking', active: true },
                                    { label: 'Auto-critique', desc: 'Quality validation', active: true },
                                    { label: 'Data analysis', desc: 'CSV / Parquet', active: false },
                                ].map(tool => (
                                    <div key={tool.label} className="flex items-center gap-2 px-2.5 py-2 rounded-lg">
                                        <div className={`w-1.5 h-1.5 rounded-full ${tool.active ? 'bg-[var(--color-accent-emerald)]' : 'bg-[var(--color-text-dim)]'}`} />
                                        <div>
                                            <p className="text-[0.65rem] text-[var(--color-text-secondary)]">{tool.label}</p>
                                            <p className="text-[0.55rem] text-[var(--color-text-dim)]">{tool.desc}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </Section>
                    </div>

                    {/* Footer */}
                    <div className="px-4 py-3 border-t border-[var(--color-border)]">
                        <div className="flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-[var(--color-accent-emerald)] animate-pulse" />
                            <span className="text-[0.6rem] text-[var(--color-text-muted)]">Connected • {sources.length} source{sources.length > 1 ? 's' : ''}</span>
                        </div>
                    </div>
                </motion.aside>
            )}
        </AnimatePresence>
    );
}
