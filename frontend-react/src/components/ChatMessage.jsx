/**
 * ChatMessage.jsx — Message block in the workspace
 * User queries as styled blocks, assistant answers with markdown rendering
 */
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { User, Bot, FileText } from 'lucide-react';
import FeedbackButtons from './FeedbackButtons';

export default function ChatMessage({ message, isLatest }) {
    const isUser = message.role === 'user';

    return (
        <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: 'spring', stiffness: 200, damping: 20 }}
            className={`px-4 sm:px-8 lg:px-16 py-3 ${isUser ? '' : ''}`}
        >
            <div className={`max-w-3xl mx-auto ${isUser ? '' : ''}`}>
                {/* Avatar + Role */}
                <div className="flex items-center gap-2.5 mb-2">
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${isUser
                        ? 'bg-[var(--color-bg-hover)] border border-[var(--color-border)]'
                        : 'bg-gradient-to-br from-indigo-500/20 to-violet-500/20 border border-indigo-500/30'
                        }`}>
                        {isUser
                            ? <User size={13} className="text-[var(--color-text-secondary)]" />
                            : <Bot size={13} className="text-[var(--color-accent-indigo)]" />
                        }
                    </div>
                    <span className={`text-[0.65rem] font-semibold uppercase tracking-wider ${isUser ? 'text-[var(--color-text-muted)]' : 'text-[var(--color-accent-indigo)]'
                        }`}>
                        {isUser ? 'You' : 'Assistant'}
                    </span>
                </div>

                {/* Content */}
                {isUser ? (
                    <div className="ml-9.5 pl-0.5">
                        <p className="text-sm text-[var(--color-text-primary)] leading-relaxed font-medium">
                            {message.content}
                        </p>
                    </div>
                ) : (
                    <div className="ml-9.5 pl-0.5">
                        {message.content ? (
                            <div className="markdown-body">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {message.content}
                                </ReactMarkdown>
                            </div>
                        ) : null}

                        {/* Source badges for completed messages */}
                        {!isLatest && message.chunks?.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-[var(--color-border)]">
                                <span className="text-[0.55rem] text-[var(--color-text-dim)] uppercase tracking-wider mr-1 self-center">Sources:</span>
                                {[...new Set(message.chunks.map(c => c.source))].map(src => (
                                    <span
                                        key={src}
                                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[0.6rem] bg-[var(--color-glass)] border border-[var(--color-border)] text-[var(--color-text-muted)]"
                                    >
                                        <FileText size={9} />
                                        {src}
                                    </span>
                                ))}
                            </div>
                        )}

                        {/* Feedback Buttons */}
                        {message.content && message.interactionId && (
                            <FeedbackButtons
                                interactionId={message.interactionId}
                                query={message.queryContext || ''}
                                answer={message.content}
                                sources={message.chunks?.map(c => c.source) || []}
                            />
                        )}
                    </div>
                )}
            </div>
        </motion.div>
    );
}
