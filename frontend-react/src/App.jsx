/**
 * App.jsx — Intelligent Workspace Layout
 * 3-panel layout: Knowledge Sidebar | Main Workspace | Context Panel
 */
import { useState, useRef, useEffect } from 'react';
import { AnimatePresence } from 'framer-motion';
import { useChat } from './hooks/useChat';
import KnowledgeSidebar from './components/KnowledgeSidebar';

import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import PipelineViz from './components/PipelineViz';
import ThinkingAnimation from './components/ThinkingAnimation';
import WelcomeScreen from './components/WelcomeScreen';
import AdminDashboard from './components/AdminDashboard';
import { PanelLeft, Layers, Trash2, Settings } from 'lucide-react';

export default function App() {
  const {
    messages, isStreaming, error,
    pipelineStep, retrievedChunks, criticResult,
    sendMessage, clearMessages,
  } = useChat();

  const [reasoning, setReasoning] = useState(false);
  const [selectedSources, setSelectedSources] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showAdmin, setShowAdmin] = useState(false);

  const messagesEndRef = useRef(null);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming, pipelineStep]);



  function handleSend(query, useReasoning = reasoning) {
    sendMessage(query, {
      sourceFilter: selectedSources.length > 0 ? selectedSources : null,
      reasoning: useReasoning,
    });
  }

  function toggleSource(src) {
    setSelectedSources(prev =>
      prev.includes(src) ? prev.filter(s => s !== src) : [...prev, src]
    );
  }

  const showPipeline = isStreaming && pipelineStep && pipelineStep !== 'done';
  const showThinking = isStreaming && pipelineStep && pipelineStep !== 'done' && pipelineStep !== 'generating';

  return (
    <div className="h-screen flex bg-[var(--color-bg-primary)] relative overflow-hidden">
      {/* Background mesh */}
      <div className="bg-mesh" />

      {/* Left Sidebar */}
      <KnowledgeSidebar
        selectedSources={selectedSources}
        onSourceToggle={toggleSource}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      {/* Main Workspace */}
      <main className="flex-1 flex flex-col relative z-10 min-w-[450px] lg:min-w-[700px]">
        {/* Top Bar */}
        <header className="shrink-0 flex items-center justify-between px-4 py-2.5 border-b border-[var(--color-border)] bg-[var(--color-bg-primary)]/80 backdrop-blur-xl">
          <div className="flex items-center gap-2">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-glass-hover)] transition-all cursor-pointer"
              >
                <PanelLeft size={16} />
              </button>
            )}
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-[var(--color-text-secondary)]">
                Intelligent Assistant
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {messages.length > 0 && (
              <button
                onClick={clearMessages}
                className="flex items-center gap-1.5 text-[0.65rem] text-[var(--color-text-muted)] hover:text-[var(--color-accent-rose)] px-2.5 py-1.5 rounded-lg hover:bg-[var(--color-accent-rose)]/5 transition-all cursor-pointer"
              >
                <Trash2 size={12} />
                <span className="hidden sm:inline">Clear</span>
              </button>
            )}

            <button
              onClick={() => setShowAdmin(true)}
              className="flex items-center gap-1.5 text-[0.65rem] text-[var(--color-text-muted)] hover:text-[var(--color-accent-indigo)] px-2.5 py-1.5 rounded-lg hover:bg-[var(--color-accent-indigo)]/5 transition-all cursor-pointer"
              title="Admin Dashboard"
            >
              <Settings size={12} />
              <span className="hidden sm:inline">Admin</span>
            </button>
          </div>
        </header>

        {/* Pipeline Visualization */}
        <AnimatePresence>
          {showPipeline && (
            <div className="shrink-0 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]/50">
              <PipelineViz currentStep={pipelineStep} />
            </div>
          )}
        </AnimatePresence>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto relative">
          {messages.length === 0 && !isStreaming ? (
            <div className="absolute inset-0">
              <WelcomeScreen onSendSuggestion={handleSend} />
            </div>
          ) : (
            <div className="py-4 min-h-full">
              {messages.map((msg, i) => (
                <ChatMessage
                  key={i}
                  message={msg}
                  isLatest={i === messages.length - 1}
                />
              ))}

              {/* Thinking animation (before tokens start) */}
              <AnimatePresence>
                {showThinking && <ThinkingAnimation step={pipelineStep} />}
              </AnimatePresence>

              <div ref={messagesEndRef} className="h-4" />
            </div>
          )}
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mx-4 sm:mx-8 lg:mx-16 mb-2 p-3 rounded-xl bg-[var(--color-accent-rose)]/10 border border-[var(--color-accent-rose)]/20 text-[var(--color-accent-rose)] text-sm flex items-center gap-2">
            <span className="shrink-0">❌</span>
            <span className="text-xs">{error}</span>
          </div>
        )}

        {/* Chat Input */}
        <ChatInput
          onSend={handleSend}
          isStreaming={isStreaming}
          reasoning={reasoning}
          onReasoningToggle={() => setReasoning(!reasoning)}
        />
      </main>

      {/* Admin Dashboard Overlay */}
      <AnimatePresence>
        {showAdmin && <AdminDashboard onClose={() => setShowAdmin(false)} />}
      </AnimatePresence>

    </div>
  );
}
