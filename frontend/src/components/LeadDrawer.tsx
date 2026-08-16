'use client';
import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, PaperPlaneRight, Lightning, CalendarBlank, ClipboardText, ChatText, User } from '@phosphor-icons/react';
import type { Lead, OutreachMessage, PipelineStage } from '../types';
import * as api from '../api';

interface LeadDrawerProps {
  lead: Lead;
  dryRun: boolean;
  onClose: () => void;
  onLeadUpdated: (lead: Lead) => void;
}

const TABS = [
  { id: 'research',    label: 'Research',      Icon: ClipboardText },
  { id: 'qualify',     label: 'Qualification', Icon: Lightning },
  { id: 'contacts',   label: 'Contacts',      Icon: User },
  { id: 'outreach',   label: 'Outreach',      Icon: PaperPlaneRight },
  { id: 'reply',      label: 'Reply Sim',     Icon: ChatText },
  { id: 'meeting',    label: 'Meeting',        Icon: CalendarBlank },
  { id: 'log',        label: 'Audit Log',      Icon: ClipboardText },
] as const;

type TabId = typeof TABS[number]['id'];

const REPLY_TEMPLATES = [
  'Can we call next Tuesday?',
  'What is your pricing model?',
  "We're not interested at this time.",
  'Send me more information.',
  'Who should I speak to about this?',
];

const PIPELINE_STAGES: PipelineStage[] = [
  'Discovered', 'Potential', 'Researching', 'Qualified',
  'Contacted', 'Interested', 'Meeting Scheduled', 'Converted',
  'Not Qualified', 'Not Interested', 'Do Not Contact',
];

function ScoreGauge({ score }: { score: number }) {
  const r = 45;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  const color = score >= 70 ? '#10b981' : score >= 40 ? '#f59e0b' : '#f43f5e';
  return (
    <svg width="110" height="110" viewBox="0 0 110 110" className="shrink-0">
      <circle cx="55" cy="55" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
      <circle
        cx="55" cy="55" r={r}
        fill="none"
        stroke={color}
        strokeWidth="8"
        strokeLinecap="round"
        strokeDasharray={`${dash} ${circ}`}
        transform="rotate(-90 55 55)"
        style={{ transition: 'stroke-dasharray 1s ease' }}
      />
      <text x="55" y="50" textAnchor="middle" fill={color} fontSize="20" fontFamily="'JetBrains Mono',monospace" fontWeight="700">
        {score}
      </text>
      <text x="55" y="67" textAnchor="middle" fill="#71717a" fontSize="9" fontFamily="'Outfit',sans-serif">
        / 100
      </text>
    </svg>
  );
}

export default function LeadDrawer({ lead: initialLead, dryRun, onClose, onLeadUpdated }: LeadDrawerProps) {
  const [lead, setLead] = useState<Lead>(initialLead);
  const [tab, setTab] = useState<TabId>('research');
  const [busy, setBusy] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [replyText, setReplyText] = useState('');
  const [meetingTime, setMeetingTime] = useState('');
  const [selectedOutreach, setSelectedOutreach] = useState<OutreachMessage | null>(
    initialLead.outreach?.[0] ?? null
  );

  const run = useCallback(async (key: string, fn: () => Promise<Lead>) => {
    setBusy(key);
    setErrorMsg(null);
    try {
      const updated = await fn();
      setLead(updated);
      onLeadUpdated(updated);
      if (updated.outreach?.length && !selectedOutreach) {
        setSelectedOutreach(updated.outreach[updated.outreach.length - 1]);
      }
    } catch (e: any) {
      console.error(e);
      let msg = e?.message || 'An error occurred';
      try {
        if (msg.startsWith('API ')) {
          const jsonPart = msg.substring(msg.indexOf(':') + 1).trim();
          const parsed = JSON.parse(jsonPart);
          if (parsed.detail) {
            msg = typeof parsed.detail === 'string' ? parsed.detail : JSON.stringify(parsed.detail);
          }
        }
      } catch {}
      setErrorMsg(msg);
    } finally {
      setBusy(null);
    }
  }, [onLeadUpdated, selectedOutreach]);

  const handleDraftEmail = () =>
    run('draft', () => api.draftEmail(lead.id));

  const handleSendEmail = (msg: OutreachMessage) =>
    run('send-' + msg.id, () => api.sendEmail(lead.id, msg.id, dryRun));

  const handleSubmitReply = () =>
    run('reply', async () => {
      const targetMsg = selectedOutreach || lead.outreach?.[0];
      if (!targetMsg) throw new Error('No outreach message available to reply to. Please draft an email first.');
      return api.submitReply(lead.id, targetMsg.id, replyText);
    });

  const handleSchedule = () =>
    run('schedule', () => api.scheduleMeeting(lead.id, meetingTime));

  const handleBriefing = () =>
    run('briefing', () => api.sendBriefing(lead.id, dryRun));

  const handleStageChange = (stage: PipelineStage) =>
    run('stage', () => api.advanceStage(lead.id, stage));

  const score = lead.qualification?.score ?? 0;

  return (
    <motion.div
      className="fixed inset-0 z-50 flex justify-end"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      {/* Backdrop */}
      <motion.div
        className="absolute inset-0"
        style={{ background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)' }}
        onClick={onClose}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      />

      {/* Drawer */}
      <motion.aside
        className="glass-bright relative z-10 flex flex-col overflow-hidden"
        style={{ width: '100%', maxWidth: 620, height: '100%' }}
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', stiffness: 160, damping: 26 }}
      >
        {/* Error banner */}
        {errorMsg && (
          <div
            className="px-5 py-2 text-xs flex items-center justify-between"
            style={{ background: 'rgba(244,63,94,0.15)', color: '#f43f5e', borderBottom: '1px solid rgba(244,63,94,0.3)' }}
          >
            <span className="truncate">{errorMsg}</span>
            <button onClick={() => setErrorMsg(null)} className="ml-2 font-bold hover:opacity-80">✕</button>
          </div>
        )}

        {/* Drawer header */}
        <div
          className="flex items-start justify-between px-5 py-4 shrink-0"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
        >
          <div>
            <h2
              className="text-base font-semibold leading-tight"
              style={{ color: '#e4e4e7', fontFamily: 'var(--font-display)' }}
            >
              {lead.company_name}
            </h2>
            <div className="flex items-center gap-2 mt-1">
              {lead.qualification && (
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full font-semibold mono ${score >= 70 ? 'badge-emerald' : score >= 40 ? 'badge-amber' : 'badge-rose'}`}
                >
                  {score}/100
                </span>
              )}
              {lead.recommended_service && (
                <span className="text-[10px] px-2 py-0.5 rounded-full badge-blue">
                  {lead.recommended_service}
                </span>
              )}
              <span className="text-[10px] px-2 py-0.5 rounded-full badge-zinc">
                {lead.pipeline_stage}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg transition-colors hover:bg-white/5"
            id="btn-close-drawer"
          >
            <X size={16} style={{ color: '#71717a' }} />
          </button>
        </div>

        {/* Stage selector */}
        <div
          className="px-5 py-2 flex items-center gap-2 shrink-0"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
        >
          <span className="text-[10px] text-zinc-600 mr-1">Stage:</span>
          <select
            value={lead.pipeline_stage}
            onChange={e => handleStageChange(e.target.value as PipelineStage)}
            className="text-[10px] bg-transparent border border-white/10 rounded px-2 py-1 outline-none"
            style={{ color: '#a1a1aa', fontFamily: 'var(--font-display)' }}
            id="select-pipeline-stage"
          >
            {PIPELINE_STAGES.map(s => (
              <option key={s} value={s} style={{ background: '#18181b' }}>{s}</option>
            ))}
          </select>
        </div>

        {/* Tabs */}
        <div
          className="flex shrink-0 overflow-x-auto px-5 gap-0"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
        >
          {TABS.map(({ id, label, Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex items-center gap-1.5 px-3 py-3 text-[11px] font-medium whitespace-nowrap transition-colors ${tab === id ? 'tab-active' : 'tab-inactive'}`}
              id={`tab-${id}`}
            >
              <Icon size={12} />
              {label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
            >
              {tab === 'research' && <TabResearch lead={lead} />}
              {tab === 'qualify'  && <TabQualify lead={lead} />}
              {tab === 'contacts' && <TabContacts lead={lead} />}
              {tab === 'outreach' && (
                <TabOutreach
                  lead={lead}
                  busy={busy}
                  dryRun={dryRun}
                  selectedOutreach={selectedOutreach}
                  onSelect={setSelectedOutreach}
                  onDraft={handleDraftEmail}
                  onSend={handleSendEmail}
                />
              )}
              {tab === 'reply' && (
                <TabReply
                  replyText={replyText}
                  setReplyText={setReplyText}
                  lead={lead}
                  selectedOutreach={selectedOutreach}
                  onSelect={setSelectedOutreach}
                  onSubmit={handleSubmitReply}
                  busy={busy}
                />
              )}
              {tab === 'meeting' && (
                <TabMeeting
                  lead={lead}
                  meetingTime={meetingTime}
                  setMeetingTime={setMeetingTime}
                  onSchedule={handleSchedule}
                  onBriefing={handleBriefing}
                  busy={busy}
                  dryRun={dryRun}
                />
              )}
              {tab === 'log' && <TabLog lead={lead} />}
            </motion.div>
          </AnimatePresence>
        </div>
      </motion.aside>
    </motion.div>
  );
}

/* ─── Tab Subcomponents ───────────────────────────────────────────────────── */

function TabResearch({ lead }: { lead: Lead }) {
  const r = lead.research;
  return (
    <div className="flex flex-col gap-4">
      <Section title="Tech Stack">
        <div className="flex flex-wrap gap-1.5">
          {r.tech_stack?.length ? r.tech_stack.map(t => (
            <span key={t} className="badge-blue text-[10px] px-2 py-0.5 rounded">{t}</span>
          )) : <Empty />}
        </div>
      </Section>
      <Section title="Buying Signals">
        <ul className="flex flex-col gap-1">
          {r.buying_signals?.length ? r.buying_signals.map((s, i) => (
            <li key={i} className="text-xs flex gap-2" style={{ color: '#a1a1aa' }}>
              <span style={{ color: '#10b981' }}>+</span> {s}
            </li>
          )) : <Empty />}
        </ul>
      </Section>
      <Section title="Recent News">
        <ul className="flex flex-col gap-1">
          {r.recent_news?.length ? r.recent_news.map((n, i) => (
            <li key={i} className="text-xs" style={{ color: '#a1a1aa' }}>- {n}</li>
          )) : <Empty />}
        </ul>
      </Section>
      <div className="grid grid-cols-2 gap-3">
        <DataPoint label="Headcount" value={r.employees_estimate || '—'} />
        <DataPoint label="Funding" value={r.funding_signal || '—'} />
      </div>
      {r.raw_notes && (
        <Section title="Raw Notes">
          <p className="text-xs leading-relaxed" style={{ color: '#71717a', whiteSpace: 'pre-wrap' }}>
            {r.raw_notes}
          </p>
        </Section>
      )}
    </div>
  );
}

function TabQualify({ lead }: { lead: Lead }) {
  const q = lead.qualification;
  if (!q) return <Empty text="Qualification has not been run on this lead yet." />;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-6">
        <ScoreGauge score={q.score} />
        <div>
          <p className="text-xs font-semibold mb-1" style={{ color: q.is_qualified ? '#10b981' : '#f43f5e' }}>
            {q.is_qualified ? 'QUALIFIED' : 'NOT QUALIFIED'}
          </p>
          <p className="text-xs leading-relaxed" style={{ color: '#a1a1aa' }}>
            {q.reasoning}
          </p>
        </div>
      </div>
      <Section title="Score Factors">
        <ul className="flex flex-col gap-1.5">
          {q.factors.map((f, i) => (
            <li key={i} className="text-xs flex gap-2" style={{ color: '#a1a1aa' }}>
              <span style={{ color: '#10b981', fontFamily: 'var(--font-mono)' }}>+</span>
              {f}
            </li>
          ))}
        </ul>
      </Section>
    </div>
  );
}

function TabContacts({ lead }: { lead: Lead }) {
  if (!lead.decision_makers?.length) return <Empty />;
  return (
    <div className="flex flex-col gap-2">
      {lead.decision_makers.map((dm, i) => (
        <div
          key={i}
          className="flex items-center gap-3 p-3 rounded-xl"
          style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.07)',
          }}
        >
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
            style={{ background: 'rgba(16,185,129,0.12)', color: '#10b981' }}
          >
            {(dm.name || dm.role)?.[0]?.toUpperCase() ?? 'P'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium truncate" style={{ color: '#e4e4e7' }}>
              {dm.name || 'Unknown'}
            </p>
            <p className="text-[10px] truncate" style={{ color: '#71717a' }}>{dm.role}</p>
            {dm.email && (
              <p className="text-[10px] truncate" style={{ color: '#52525b', fontFamily: 'var(--font-mono)' }}>
                {dm.email}
              </p>
            )}
          </div>
          <span
            className="text-[9px] px-1.5 py-0.5 rounded badge-zinc mono shrink-0"
          >
            P{dm.priority}
          </span>
        </div>
      ))}
    </div>
  );
}

function TabOutreach({
  lead, busy, dryRun, selectedOutreach, onSelect, onDraft, onSend,
}: {
  lead: Lead;
  busy: string | null;
  dryRun: boolean;
  selectedOutreach: OutreachMessage | null;
  onSelect: (m: OutreachMessage) => void;
  onDraft: () => void;
  onSend: (m: OutreachMessage) => void;
}) {
  const statusClass = (s: string) => {
    if (s === 'Sent') return 'badge-blue';
    if (s === 'Replied') return 'badge-emerald';
    if (s === 'Bounced') return 'badge-rose';
    return 'badge-amber'; // Drafted, Followed Up
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2">
        <button
          className="btn-primary flex items-center gap-1.5 text-xs px-3 py-2"
          onClick={onDraft}
          disabled={busy === 'draft'}
          id="btn-draft-email"
        >
          <Lightning size={12} weight="fill" />
          {busy === 'draft' ? 'Drafting...' : 'Draft Email with AI'}
        </button>
        {dryRun && (
          <span className="badge-amber text-[10px] px-2 py-1 rounded-lg flex items-center">
            Dry-Run ON
          </span>
        )}
      </div>

      {lead.outreach.length === 0 ? (
        <Empty text="No outreach messages yet. Click Draft Email to generate one." />
      ) : (
        lead.outreach.map(msg => (
          <div
            key={msg.id}
            className={`rounded-xl p-3 cursor-pointer transition-colors ${selectedOutreach?.id === msg.id ? 'ring-1 ring-emerald-500/40' : ''}`}
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: selectedOutreach?.id === msg.id ? '1px solid rgba(16,185,129,0.3)' : '1px solid rgba(255,255,255,0.07)',
            }}
            onClick={() => onSelect(msg)}
          >
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-medium truncate flex-1" style={{ color: '#e4e4e7' }}>
                {msg.subject}
              </p>
              <span className={`text-[10px] px-1.5 py-0.5 rounded ml-2 shrink-0 ${statusClass(msg.status)}`}>
                {msg.status}
              </span>
            </div>
            <p className="text-[11px] leading-relaxed line-clamp-3" style={{ color: '#71717a' }}>
              {msg.body}
            </p>
            {msg.evidence_used?.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {msg.evidence_used.map(e => (
                  <span key={e} className="text-[9px] px-1.5 py-0.5 rounded badge-zinc">{e}</span>
                ))}
              </div>
            )}
            <div className="flex gap-2 mt-2">
              <button
                className="btn-primary text-[10px] px-2.5 py-1"
                onClick={e => { e.stopPropagation(); onSend(msg); }}
                disabled={busy === 'send-' + msg.id}
                id={`btn-send-${msg.id}`}
              >
                {busy === 'send-' + msg.id ? 'Sending...' : 'Send Email'}
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

function TabReply({
  replyText, setReplyText, lead, selectedOutreach, onSelect, onSubmit, busy,
}: {
  replyText: string;
  setReplyText: (s: string) => void;
  lead: Lead;
  selectedOutreach: OutreachMessage | null;
  onSelect: (m: OutreachMessage) => void;
  onSubmit: () => void;
  busy: string | null;
}) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs" style={{ color: '#71717a' }}>
        Simulate an inbound reply from a prospect. Select the outreach message being replied to, then submit.
      </p>

      {/* Select outreach */}
      {lead.outreach.length > 0 && (
        <div className="flex flex-col gap-1">
          <label className="text-[10px]" style={{ color: '#71717a' }}>Replying to:</label>
          <select
            value={selectedOutreach?.id ?? ''}
            onChange={e => {
              const m = lead.outreach.find(o => o.id === e.target.value);
              if (m) onSelect(m);
            }}
            className="text-xs bg-transparent border border-white/10 rounded px-2 py-1.5 outline-none"
            style={{ color: '#a1a1aa' }}
            id="select-reply-outreach"
          >
            <option value="" style={{ background: '#18181b' }}>— Choose message —</option>
            {lead.outreach.map(m => (
              <option key={m.id} value={m.id} style={{ background: '#18181b' }}>
                {m.subject}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Templates */}
      <div className="flex flex-col gap-1">
        <label className="text-[10px]" style={{ color: '#71717a' }}>Templates:</label>
        <div className="flex flex-wrap gap-1.5">
          {REPLY_TEMPLATES.map(t => (
            <button
              key={t}
              onClick={() => setReplyText(t)}
              className="btn-ghost text-[10px] px-2.5 py-1"
              id={`template-${t.slice(0, 10).replace(/\W/g, '-')}`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <textarea
        value={replyText}
        onChange={e => setReplyText(e.target.value)}
        rows={4}
        placeholder="Type prospect reply here..."
        className="w-full text-xs px-3 py-2 rounded-xl outline-none resize-none"
        style={{
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.08)',
          color: '#e4e4e7',
          fontFamily: 'var(--font-display)',
        }}
        id="textarea-reply-input"
      />

      <button
        className="btn-primary text-xs px-4 py-2 self-start"
        onClick={onSubmit}
        disabled={busy === 'reply'}
        id="btn-submit-reply"
      >
        {busy === 'reply' ? 'Classifying...' : 'Submit Reply'}
      </button>

      {/* Show classification result */}
      {lead.outreach.find(m => m.reply_classification)?.reply_classification && (() => {
        const cls = lead.outreach.find(m => m.reply_classification)?.reply_classification;
        const cls2Badge = (c: string) => {
          if (c.includes('Meeting') || c.includes('Interested') || c.includes('Positive')) return 'badge-emerald';
          if (c.includes('Not') || c.includes('Objection')) return 'badge-rose';
          return 'badge-amber';
        };
        return (
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs" style={{ color: '#71717a' }}>Classification:</span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls2Badge(cls ?? '')}`}>
              {cls}
            </span>
          </div>
        );
      })()}
    </div>
  );
}

function TabMeeting({
  lead, meetingTime, setMeetingTime, onSchedule, onBriefing, busy, dryRun,
}: {
  lead: Lead;
  meetingTime: string;
  setMeetingTime: (s: string) => void;
  onSchedule: () => void;
  onBriefing: () => void;
  busy: string | null;
  dryRun: boolean;
}) {
  const meeting = lead.meeting;
  return (
    <div className="flex flex-col gap-4">
      {meeting?.meeting_link && (
        <div
          className="p-3 rounded-xl flex flex-col gap-1"
          style={{ background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.2)' }}
        >
          <p className="text-xs font-medium" style={{ color: '#10b981' }}>Meeting Scheduled</p>
          <p className="text-[11px]" style={{ color: '#a1a1aa' }}>
            {meeting.scheduled_time || '—'}
          </p>
          <a
            href={meeting.meeting_link}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[11px] underline"
            style={{ color: '#60a5fa', fontFamily: 'var(--font-mono)' }}
          >
            {meeting.meeting_link}
          </a>
        </div>
      )}

      <div className="flex flex-col gap-1">
        <label htmlFor="meeting-time" className="text-[10px]" style={{ color: '#71717a' }}>
          Schedule Date & Time
        </label>
        <input
          id="meeting-time"
          type="datetime-local"
          value={meetingTime}
          onChange={e => setMeetingTime(e.target.value)}
          className="text-xs px-3 py-2 rounded-lg outline-none"
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            color: '#e4e4e7',
            colorScheme: 'dark',
          }}
        />
      </div>

      <div className="flex gap-2">
        <button
          className="btn-primary text-xs px-4 py-2 flex items-center gap-1.5"
          onClick={onSchedule}
          disabled={busy === 'schedule' || !meetingTime}
          id="btn-schedule-meeting"
        >
          <CalendarBlank size={13} weight="fill" />
          {busy === 'schedule' ? 'Booking...' : 'Book Meeting'}
        </button>
        <button
          className="btn-ghost text-xs px-4 py-2 flex items-center gap-1.5"
          onClick={onBriefing}
          disabled={busy === 'briefing'}
          id="btn-send-briefing"
        >
          <ClipboardText size={13} weight="fill" />
          {busy === 'briefing' ? 'Sending...' : (dryRun ? 'Preview Briefing' : 'Send AE Briefing')}
        </button>
      </div>

      {meeting?.briefing && (
        <Section title="AE Briefing Preview">
          <p className="text-[11px] leading-relaxed whitespace-pre-wrap" style={{ color: '#a1a1aa' }}>
            {meeting.briefing}
          </p>
        </Section>
      )}
    </div>
  );
}

function TabLog({ lead }: { lead: Lead }) {
  if (!lead.memory_log?.length) return <Empty text="No audit log entries yet." />;
  return (
    <div className="flex flex-col gap-0 relative">
      <div className="absolute left-[7px] top-0 bottom-0 w-px" style={{ background: 'rgba(255,255,255,0.06)' }} />
      {lead.memory_log.map((entry, i) => (
        <div key={i} className="flex gap-3 items-start pb-3 pl-1">
          <div className="w-3.5 h-3.5 rounded-full shrink-0 mt-0.5 z-10" style={{ background: '#18181b', border: '2px solid rgba(16,185,129,0.4)' }} />
          <p className="text-[11px] leading-relaxed" style={{ color: '#71717a' }}>{entry}</p>
        </div>
      ))}
    </div>
  );
}

/* ─── Helpers ─────────────────────────────────────────────────────────────── */

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-[10px] uppercase tracking-widest font-semibold" style={{ color: '#3f3f46' }}>
        {title}
      </p>
      {children}
    </div>
  );
}

function DataPoint({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="flex flex-col gap-0.5 p-2.5 rounded-lg"
      style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}
    >
      <span className="text-[9px] uppercase tracking-widest" style={{ color: '#52525b' }}>{label}</span>
      <span className="text-xs mono" style={{ color: '#a1a1aa' }}>{value}</span>
    </div>
  );
}

function Empty({ text = 'No data available.' }: { text?: string }) {
  return (
    <p className="text-xs text-zinc-600 py-2">{text}</p>
  );
}
