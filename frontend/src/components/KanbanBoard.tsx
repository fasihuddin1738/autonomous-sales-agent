'use client';
import { AnimatePresence, motion } from 'framer-motion';
import { Plus } from '@phosphor-icons/react';
import type { Lead, PipelineStage } from '../types';
import LeadCard from './LeadCard';

const PRIMARY_STAGES: PipelineStage[] = [
  'Discovered', 'Researching', 'Qualified', 'Contacted',
  'Interested', 'Meeting Scheduled', 'Converted',
];
const NEGATIVE_STAGES: PipelineStage[] = [
  'Not Qualified', 'Not Interested', 'Do Not Contact',
];

const STAGE_COLORS: Record<PipelineStage, string> = {
  'Discovered':       '#71717a',
  'Potential':        '#a1a1aa',
  'Researching':      '#60a5fa',
  'Qualified':        '#10b981',
  'Contacted':        '#f59e0b',
  'Interested':       '#10b981',
  'Meeting Scheduled':'#a78bfa',
  'Converted':        '#10b981',
  'Not Qualified':    '#f43f5e',
  'Not Interested':   '#f43f5e',
  'Do Not Contact':   '#f43f5e',
};

interface KanbanBoardProps {
  leads: Lead[];
  showNegative: boolean;
  onToggleNegative: () => void;
  onSelectLead: (lead: Lead) => void;
}

export default function KanbanBoard({
  leads, showNegative, onToggleNegative, onSelectLead,
}: KanbanBoardProps) {
  const visibleStages = showNegative
    ? [...PRIMARY_STAGES, ...NEGATIVE_STAGES]
    : PRIMARY_STAGES;

  const getLeads = (stage: PipelineStage) =>
    leads.filter(l => l.pipeline_stage === stage);

  if (leads.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center"
          style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}
        >
          <Plus size={24} style={{ color: '#52525b' }} />
        </div>
        <div className="text-center">
          <p className="text-sm font-medium" style={{ color: '#71717a' }}>No leads yet</p>
          <p className="text-xs mt-1" style={{ color: '#3f3f46' }}>
            Click "Seed Data" to populate mock leads, or configure ICP and Launch Pipeline.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Filter toggle */}
      <div className="flex justify-end">
        <button
          className="btn-ghost text-xs px-3 py-1.5"
          onClick={onToggleNegative}
          id="btn-toggle-negative-stages"
        >
          {showNegative ? 'Hide Rejected' : 'Show Rejected / DNC'}
        </button>
      </div>

      {/* Kanban track */}
      <div className="kanban-track pb-2">
        {visibleStages.map(stage => {
          const stageLeads = getLeads(stage);
          const color = STAGE_COLORS[stage];
          return (
            <div
              key={stage}
              className="kanban-col glass rounded-xl flex flex-col"
              style={{ width: 220, minHeight: 280 }}
            >
              {/* Column header */}
              <div
                className="flex items-center justify-between px-3 py-2.5"
                style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}
              >
                <div className="flex items-center gap-1.5">
                  <span
                    className="w-1.5 h-1.5 rounded-full shrink-0"
                    style={{ background: color }}
                  />
                  <span
                    className="text-[10px] font-semibold uppercase tracking-widest"
                    style={{ color }}
                  >
                    {stage}
                  </span>
                </div>
                <span
                  className="mono text-[10px] px-1.5 py-0.5 rounded"
                  style={{ background: 'rgba(255,255,255,0.05)', color: '#71717a' }}
                >
                  {stageLeads.length}
                </span>
              </div>

              {/* Cards */}
              <div className="flex flex-col gap-2 p-2 flex-1">
                <AnimatePresence>
                  {stageLeads.map(lead => (
                    <LeadCard
                      key={lead.id}
                      lead={lead}
                      onClick={() => onSelectLead(lead)}
                    />
                  ))}
                </AnimatePresence>

                {stageLeads.length === 0 && (
                  <div
                    className="flex-1 flex items-center justify-center rounded-lg"
                    style={{ minHeight: 60, border: '1px dashed rgba(255,255,255,0.05)' }}
                  >
                    <span className="text-[10px]" style={{ color: '#3f3f46' }}>Empty</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 flex-wrap pt-1">
        {[
          { label: 'Qualified / Converted', color: '#10b981' },
          { label: 'Pending / In Progress', color: '#f59e0b' },
          { label: 'Rejected', color: '#f43f5e' },
        ].map(({ label, color }) => (
          <div key={label} className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: color }} />
            <span className="text-[10px]" style={{ color: '#52525b' }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
