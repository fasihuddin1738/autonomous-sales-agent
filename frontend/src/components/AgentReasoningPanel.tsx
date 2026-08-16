'use client';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, CaretDown, CaretUp } from '@phosphor-icons/react';
import type { AgentLogEntry } from '../types';

interface AgentReasoningPanelProps {
  logs: AgentLogEntry[];
}

export default function AgentReasoningPanel({ logs }: AgentReasoningPanelProps) {
  const [open, setOpen] = useState(false);

  // Only show clean info logs — errors are shown in the status bar, not here
  const infoLogs = logs.filter(e => e.kind === 'info');

  return (
    <div
      className="glass rounded-xl overflow-hidden"
      style={{ border: '1px solid rgba(255,255,255,0.07)' }}
    >
      {/* Header */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
        id="btn-toggle-reasoning"
      >
        <div className="flex items-center gap-2.5">
          <motion.div
            animate={{ rotate: [0, 360] }}
            transition={{ repeat: Infinity, duration: 6, ease: 'linear' }}
          >
            <Brain size={16} style={{ color: '#10b981' }} weight="duotone" />
          </motion.div>
          <span
            className="text-xs font-medium tracking-wide"
            style={{ color: '#a1a1aa', fontFamily: 'var(--font-display)' }}
          >
            Agent Reasoning Stream
          </span>
          <span
            className="text-xs px-2 py-0.5 rounded-full"
            style={{
              background: 'rgba(16,185,129,0.1)',
              color: '#10b981',
              border: '1px solid rgba(16,185,129,0.2)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            {infoLogs.length} steps
          </span>
        </div>
        {open ? (
          <CaretUp size={13} style={{ color: '#71717a' }} />
        ) : (
          <CaretDown size={13} style={{ color: '#71717a' }} />
        )}
      </button>

      {/* Log stream */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 160, damping: 22 }}
            style={{ overflow: 'hidden' }}
          >
            <div
              className="px-4 pb-4 flex flex-col gap-1.5 max-h-56 overflow-y-auto"
              style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}
            >
              {infoLogs.length === 0 ? (
                <p className="text-xs text-zinc-600 pt-3">
                  No agent activity yet. Launch the pipeline to see reasoning logs.
                </p>
              ) : (
                infoLogs.map((entry, i) => (
                  <motion.div
                    key={i}
                    className="log-entry flex gap-2 items-start pt-2"
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.03 }}
                  >
                    <span
                      className="shrink-0 mt-0.5 text-xs"
                      style={{
                        color: '#10b981',
                        fontFamily: 'var(--font-mono)',
                        minWidth: '72px',
                      }}
                    >
                      {entry.timestamp}
                    </span>
                    <span
                      className="text-xs leading-relaxed"
                      style={{ color: entry.message.startsWith('  ') ? '#71717a' : '#a1a1aa' }}
                    >
                      {entry.message}
                    </span>
                  </motion.div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
