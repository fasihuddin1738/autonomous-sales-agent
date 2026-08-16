'use client';
import type { Lead } from '../types';

interface KPIStripProps {
  leads: Lead[];
}

export default function KPIStrip({ leads }: KPIStripProps) {
  const total = leads.length;
  const qualified = leads.filter(l => l.qualification?.is_qualified).length;
  const contacted = leads.filter(l =>
    ['Contacted', 'Interested', 'Meeting Scheduled', 'Converted'].includes(l.pipeline_stage)
  ).length;
  const meetings = leads.filter(l => l.pipeline_stage === 'Meeting Scheduled').length;
  const converted = leads.filter(l => l.pipeline_stage === 'Converted').length;
  const avgScore = total
    ? Math.round(leads.reduce((s, l) => s + (l.qualification?.score ?? 0), 0) / total)
    : 0;

  const kpis = [
    { label: 'Total Leads', value: total, color: '#a1a1aa' },
    { label: 'Qualified', value: qualified, color: '#10b981' },
    { label: 'Contacted', value: contacted, color: '#60a5fa' },
    { label: 'Meetings', value: meetings, color: '#f59e0b' },
    { label: 'Converted', value: converted, color: '#10b981' },
    { label: 'Avg Score', value: `${avgScore}/100`, color: '#10b981' },
  ];

  return (
    <div
      className="glass rounded-xl px-4 py-3 flex items-center gap-0 divide-x"
      style={{ divideColor: 'rgba(255,255,255,0.06)' }}
    >
      {kpis.map(({ label, value, color }) => (
        <div key={label} className="flex-1 flex flex-col items-center gap-0.5 px-3">
          <span
            className="mono text-xl font-semibold leading-none"
            style={{ color }}
          >
            {value}
          </span>
          <span className="text-[10px] uppercase tracking-widest" style={{ color: '#52525b' }}>
            {label}
          </span>
        </div>
      ))}
    </div>
  );
}
