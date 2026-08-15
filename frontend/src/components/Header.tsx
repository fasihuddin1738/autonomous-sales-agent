'use client';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RocketLaunch, ArrowsClockwise, Flask, ArrowCounterClockwise,
  CircleDashed,
} from '@phosphor-icons/react';

interface HeaderProps {
  agentStatus: string;
  mockMode: boolean;
  dryRun: boolean;
  onToggleMock: () => void;
  onToggleDryRun: () => void;
  onLaunch: () => void;
  onScanFollowUps: () => void;
  onSeedData: () => void;
  onReset: () => void;
  loading: boolean;
}

export default function Header({
  agentStatus, mockMode, dryRun,
  onToggleMock, onToggleDryRun,
  onLaunch, onScanFollowUps, onSeedData, onReset,
  loading,
}: HeaderProps) {
  return (
    <header
      className="glass sticky top-0 z-40 w-full"
      style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}
    >
      <div className="max-w-[1400px] mx-auto px-5 py-3 flex flex-col gap-2">
        {/* Row 1 — brand + controls */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          {/* Branding */}
          <div className="flex items-center gap-2.5">
            <span
              className="pulse-dot w-2 h-2 rounded-full"
              style={{ background: '#10b981', boxShadow: '0 0 6px #10b981' }}
            />
            <h1
              className="text-sm font-semibold tracking-tight"
              style={{ fontFamily: 'var(--font-display)', color: '#e4e4e7' }}
            >
              NexaFlow AI
              <span className="text-zinc-500 font-normal ml-1 hidden sm:inline">
                — Autonomous B2B Sales Command Center
              </span>
            </h1>
          </div>

          {/* Toggles */}
          <div className="flex items-center gap-3 flex-wrap">
            <Toggle label="Mock" active={mockMode} onToggle={onToggleMock} />
            <Toggle label="Dry-Run" active={dryRun} onToggle={onToggleDryRun} />
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 flex-wrap">
            <button
              className="btn-primary flex items-center gap-1.5 text-xs px-3 py-1.5"
              onClick={onLaunch}
              disabled={loading}
              id="btn-launch-pipeline"
            >
              {loading
                ? <CircleDashed size={13} className="animate-spin" />
                : <RocketLaunch size={13} weight="fill" />}
              Launch Pipeline
            </button>
            <button
              className="btn-ghost flex items-center gap-1.5 text-xs px-3 py-1.5"
              onClick={onScanFollowUps}
              id="btn-scan-followups"
            >
              <ArrowsClockwise size={13} />
              Follow-ups
            </button>
            <button
              className="btn-ghost flex items-center gap-1.5 text-xs px-3 py-1.5"
              onClick={onSeedData}
              id="btn-seed-data"
            >
              <Flask size={13} weight="fill" />
              Seed Data
            </button>
            <button
              className="btn-ghost flex items-center gap-1 text-xs px-2.5 py-1.5"
              onClick={onReset}
              id="btn-reset"
            >
              <ArrowCounterClockwise size={13} />
              Reset
            </button>
          </div>
        </div>

        {/* Row 2 — agent status pill */}
        <AnimatePresence mode="wait">
          <motion.div
            key={agentStatus}
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ type: 'spring', stiffness: 200, damping: 25 }}
            className="flex items-center gap-2 self-start"
          >
            <span
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium"
              style={{
                background: 'rgba(16,185,129,0.1)',
                border: '1px solid rgba(16,185,129,0.25)',
                color: '#10b981',
                fontFamily: 'var(--font-mono)',
              }}
            >
              <span
                className="w-1.5 h-1.5 rounded-full pulse-dot"
                style={{ background: '#10b981' }}
              />
              {agentStatus}
            </span>
          </motion.div>
        </AnimatePresence>
      </div>
    </header>
  );
}

function Toggle({ label, active, onToggle }: { label: string; active: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      className="flex items-center gap-2 text-xs"
      style={{ color: active ? '#10b981' : '#71717a' }}
      id={`toggle-${label.toLowerCase().replace(/[^a-z]/g, '-')}`}
    >
      <span
        className="relative w-7 h-4 rounded-full transition-colors duration-200"
        style={{ background: active ? 'rgba(16,185,129,0.3)' : 'rgba(255,255,255,0.06)' }}
      >
        <motion.span
          className="absolute top-0.5 w-3 h-3 rounded-full"
          style={{ background: active ? '#10b981' : '#52525b' }}
          animate={{ left: active ? '14px' : '2px' }}
          transition={{ type: 'spring', stiffness: 300, damping: 28 }}
        />
      </span>
      {label}
    </button>
  );
}
