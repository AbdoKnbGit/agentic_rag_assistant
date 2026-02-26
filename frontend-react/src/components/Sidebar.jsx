/**
 * Sidebar.jsx — Collapsible sidebar with student profile, sources, upload, links
 */
import { useState, useEffect, useRef } from 'react';
import {
    GraduationCap, Target, FileText, Upload, Trash2, Link,
    ChevronDown, CheckCircle2, XCircle, Loader2, BookOpen,
    BarChart3, Search, PanelLeftClose, PanelLeft, Plus, AlertCircle
} from 'lucide-react';
import { getSources, uploadFile } from '../api';

const LEVELS = ['débutant', 'intermédiaire', 'avancé', 'expert'];
const GOALS = ['comprendre', "s'entraîner", 'réviser', 'examen'];

const LEVEL_COLORS = {
    'débutant': 'from-green-400 to-emerald-500',
    'intermédiaire': 'from-blue-400 to-indigo-500',
    'avancé': 'from-purple-400 to-violet-500',
    'expert': 'from-orange-400 to-red-500',
};

export default function Sidebar({ profile, onProfileChange, isOpen, onToggle }) {
    const [sources, setSources] = useState([]);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadStatus, setUploadStatus] = useState(null); // 'success' | 'error' | null
    const [dragOver, setDragOver] = useState(false);
    const fileInputRef = useRef(null);

    // Load sources
    useEffect(() => {
        loadSources();
        const interval = setInterval(loadSources, 15000);
        return () => clearInterval(interval);
    }, []);

    async function loadSources() {
        const s = await getSources();
        setSources(s);
    }

    async function handleUpload(file) {
        if (!file) return;
        setIsUploading(true);
        setUploadStatus(null);
        try {
            await uploadFile(file);
            setUploadStatus('success');
            await loadSources();
            setTimeout(() => setUploadStatus(null), 3000);
        } catch (err) {
            setUploadStatus('error');
            setTimeout(() => setUploadStatus(null), 4000);
        } finally {
            setIsUploading(false);
        }
    }

    function handleDrop(e) {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files[0];
        if (file) handleUpload(file);
    }

    function extractFilename(path) {
        return path.split('/').pop().split('\\').pop();
    }

    return (
        <>
            {/* Mobile overlay */}
            {isOpen && (
                <div
                    className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
                    onClick={onToggle}
                />
            )}

            {/* Sidebar */}
            <aside className={`
        fixed top-0 left-0 h-full z-50 lg:relative lg:z-0
        w-80 bg-[var(--color-bg-secondary)]/95 backdrop-blur-xl
        border-r border-[var(--color-border)]
        flex flex-col
        transition-transform duration-300 ease-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0 lg:w-0 lg:overflow-hidden lg:border-0'}
      `}>
                {/* Header */}
                <div className="p-5 border-b border-[var(--color-border)]">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/25">
                                <GraduationCap size={20} className="text-white" />
                            </div>
                            <div>
                                <h1 className="text-sm font-bold gradient-text">RAG Assistant</h1>
                                <p className="text-[0.65rem] text-[var(--color-text-muted)] uppercase tracking-widest">Pédagogique</p>
                            </div>
                        </div>
                        <button
                            onClick={onToggle}
                            className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-white/5 transition-all cursor-pointer"
                        >
                            <PanelLeftClose size={18} />
                        </button>
                    </div>
                </div>

                {/* Content — scrollable */}
                <div className="flex-1 overflow-y-auto p-5 space-y-6">

                    {/* Student Profile */}
                    <Section icon={GraduationCap} title="Profil Étudiant">
                        <div className="space-y-3">
                            <div>
                                <label className="text-[0.7rem] font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-1.5 block">
                                    Niveau
                                </label>
                                <div className="grid grid-cols-2 gap-1.5">
                                    {LEVELS.map(lvl => (
                                        <button
                                            key={lvl}
                                            onClick={() => onProfileChange({ ...profile, level: lvl })}
                                            className={`
                        text-xs py-2 px-3 rounded-lg font-medium transition-all duration-200 capitalize cursor-pointer
                        ${profile.level === lvl
                                                    ? `bg-gradient-to-r ${LEVEL_COLORS[lvl]} text-white shadow-md`
                                                    : 'bg-white/5 text-[var(--color-text-secondary)] hover:bg-white/10 hover:text-[var(--color-text-primary)]'
                                                }
                      `}
                                        >
                                            {lvl}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            <div>
                                <label className="text-[0.7rem] font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-1.5 block">
                                    Objectif
                                </label>
                                <div className="grid grid-cols-2 gap-1.5">
                                    {GOALS.map(goal => (
                                        <button
                                            key={goal}
                                            onClick={() => onProfileChange({ ...profile, goal })}
                                            className={`
                        text-xs py-2 px-3 rounded-lg font-medium transition-all duration-200 capitalize cursor-pointer
                        ${profile.goal === goal
                                                    ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-md'
                                                    : 'bg-white/5 text-[var(--color-text-secondary)] hover:bg-white/10 hover:text-[var(--color-text-primary)]'
                                                }
                      `}
                                        >
                                            {goal}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </Section>

                    {/* Indexed Documents */}
                    <Section icon={FileText} title="Documents Indexés" badge={sources.length}>
                        {sources.length > 0 ? (
                            <div className="space-y-1.5">
                                {sources.map((source, i) => (
                                    <div
                                        key={i}
                                        className="flex items-center gap-2.5 p-2.5 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] group transition-colors"
                                    >
                                        <FileText size={14} className="text-indigo-400 shrink-0" />
                                        <span className="text-xs text-[var(--color-text-secondary)] truncate flex-1" title={source}>
                                            {extractFilename(source)}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-xs text-[var(--color-text-muted)] bg-white/[0.02] rounded-lg p-3 text-center">
                                <AlertCircle size={16} className="mx-auto mb-1 opacity-50" />
                                Aucun document indexé
                            </div>
                        )}
                    </Section>

                    {/* Upload */}
                    <Section icon={Upload} title="Uploader">
                        <div
                            className={`drop-zone rounded-xl p-6 text-center cursor-pointer transition-all ${dragOver ? 'drag-over' : ''}`}
                            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                            onDragLeave={() => setDragOver(false)}
                            onDrop={handleDrop}
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".pdf,.docx,.csv,.parquet,.txt"
                                className="hidden"
                                onChange={(e) => handleUpload(e.target.files[0])}
                            />
                            {isUploading ? (
                                <Loader2 size={24} className="mx-auto text-indigo-400 animate-spin mb-2" />
                            ) : (
                                <Plus size={24} className="mx-auto text-[var(--color-text-muted)] mb-2" />
                            )}
                            <p className="text-xs text-[var(--color-text-muted)]">
                                {isUploading ? 'Indexation en cours...' : 'Glisser ou cliquer'}
                            </p>
                            <p className="text-[0.65rem] text-[var(--color-text-muted)] opacity-50 mt-1">
                                PDF, DOCX, CSV, TXT, Parquet
                            </p>
                        </div>

                        {uploadStatus === 'success' && (
                            <div className="mt-2 flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 rounded-lg p-2.5 animate-fadeIn">
                                <CheckCircle2 size={14} /> Document indexé avec succès !
                            </div>
                        )}
                        {uploadStatus === 'error' && (
                            <div className="mt-2 flex items-center gap-2 text-xs text-red-400 bg-red-500/10 rounded-lg p-2.5 animate-fadeIn">
                                <XCircle size={14} /> Erreur lors de l'upload
                            </div>
                        )}
                    </Section>

                    {/* Quick Links */}
                    <Section icon={Link} title="Liens Rapides">
                        <div className="space-y-1">
                            <QuickLink icon={BookOpen} label="API Docs" href="http://localhost:8000/docs" />
                            <QuickLink icon={BarChart3} label="Grafana" href="http://localhost:3000" />
                            <QuickLink icon={Search} label="Qdrant UI" href="http://localhost:6333/dashboard" />
                        </div>
                    </Section>
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-[var(--color-border)]">
                    <div className="flex items-center gap-2 text-[0.65rem] text-[var(--color-text-muted)]">
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        <span>Ollama (Mistral) • LangGraph</span>
                    </div>
                </div>
            </aside>
        </>
    );
}

function Section({ icon: Icon, title, badge, children }) {
    return (
        <div>
            <div className="flex items-center gap-2 mb-3">
                <Icon size={14} className="text-[var(--color-accent-primary)]" />
                <span className="text-[0.72rem] font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">
                    {title}
                </span>
                {badge != null && badge > 0 && (
                    <span className="ml-auto text-[0.6rem] bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full font-semibold">
                        {badge}
                    </span>
                )}
            </div>
            {children}
        </div>
    );
}

function QuickLink({ icon: Icon, label, href }) {
    return (
        <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2.5 p-2.5 rounded-lg text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-white/5 transition-all group"
        >
            <Icon size={14} className="text-[var(--color-text-muted)] group-hover:text-indigo-400 transition-colors" />
            {label}
        </a>
    );
}
