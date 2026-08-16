'use client';
import { useRef } from 'react';
import { motion } from 'framer-motion';
import { Buildings, ArrowRight } from '@phosphor-icons/react';
import type { Lead } from '../types';

interface LeadCardProps {
  lead: Lead;
  onClick: () => void;
}

function scoreBadgeClass(score: number) {
  if (score >= 70) return 'badge-emerald';
  if (score >= 40) return 'badge-amber';
  return 'badge-rose';
}

export default function LeadCard({ lead, onClick }: LeadCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = cardRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = (e.clientX - cx) / (rect.width / 2);
    const dy = (e.clientY - cy) / (rect.height / 2);
    el.style.transform = `perspective(600px) rotateX(${-dy * 5}deg) rotateY(${dx * 5}deg)`;
  };

  const handleMouseLeave = () => {
    if (cardRef.current) cardRef.current.style.transform = '';
  };

  const score = lead.qualification?.score ?? 0;
  const dm = lead.decision_makers?.[0];

  return (
    <motion.div
      layout
      layoutId={lead.id}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 160, damping: 22 }}
      ref={cardRef}
      className="tilt-card glass rounded-xl p-3 cursor-pointer select-none"
      style={{ minWidth: 0 }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onClick={onClick}
      id={`lead-card-${lead.id}`}
    >
      {/* Company header */}
      <div className="flex items-start gap-2 mb-2">
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
          style={{ background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.2)' }}
        >
          <Buildings size={13} weight="fill" style={{ color: '#10b981' }} />
        </div>
        <div className="min-w-0">
          <p
            className="text-xs font-semibold leading-tight truncate"
            style={{ color: '#e4e4e7' }}
          >
            {lead.company_name}
          </p>
          <p className="text-[10px] truncate" style={{ color: '#52525b' }}>
            {lead.research?.website || 'No website'}
          </p>
        </div>
      </div>

      {/* Score + service */}
      <div className="flex flex-wrap gap-1 mb-2">
        {lead.qualification && (
          <span className={`text-[10px] px-1.5 py-0.5 rounded-md font-semibold mono ${scoreBadgeClass(score)}`}>
            {score}/100
          </span>
        )}
        {lead.recommended_service && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-md badge-blue truncate max-w-[120px]">
            {lead.recommended_service}
          </span>
        )}
      </div>

      {/* Decision maker */}
      {dm && (
        <div className="flex items-center gap-1.5 mb-2.5">
          <div
            className="w-5 h-5 rounded-full text-[9px] font-bold flex items-center justify-center shrink-0"
            style={{ background: 'rgba(255,255,255,0.06)', color: '#71717a' }}
          >
            {(dm.name || dm.role)?.[0]?.toUpperCase() ?? 'P'}
          </div>
          <div className="min-w-0">
            <p className="text-[10px] truncate" style={{ color: '#a1a1aa' }}>
              {dm.name || 'Unknown'}
            </p>
            <p className="text-[9px] truncate" style={{ color: '#52525b' }}>
              {dm.role}
            </p>
          </div>
        </div>
      )}

      {/* CTA */}
      <button
        className="w-full flex items-center justify-center gap-1 text-[10px] py-1.5 rounded-lg transition-colors"
        style={{
          background: 'rgba(16,185,129,0.08)',
          border: '1px solid rgba(16,185,129,0.2)',
          color: '#10b981',
        }}
        onClick={e => { e.stopPropagation(); onClick(); }}
        id={`btn-view-${lead.id}`}
      >
        Intelligence & Studio
        <ArrowRight size={10} weight="bold" />
      </button>
    </motion.div>
  );
}
