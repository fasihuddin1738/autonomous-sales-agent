'use client';
import { MagnifyingGlass } from '@phosphor-icons/react';
import type { ICP } from '../types';

interface ICPPanelProps {
  icp: ICP;
  onChange: (icp: ICP) => void;
  onScan: () => void;
  loading: boolean;
}

const fields: { key: keyof ICP; label: string; placeholder: string }[] = [
  { key: 'target_location', label: 'Location', placeholder: 'Karachi, Pakistan' },
  { key: 'target_industry', label: 'Industry', placeholder: 'E-commerce' },
  { key: 'company_size', label: 'Company Size', placeholder: '50-300 employees' },
  { key: 'special_focus', label: 'Special Focus', placeholder: 'High WhatsApp inquiry volume' },
];

export default function ICPPanel({ icp, onChange, onScan, loading }: ICPPanelProps) {
  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <span
          className="text-xs font-semibold tracking-widest uppercase"
          style={{ color: '#52525b', letterSpacing: '0.1em' }}
        >
          ICP Target Configuration
        </span>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {fields.map(({ key, label, placeholder }) => (
          <div key={key} className="flex flex-col gap-1">
            <label
              htmlFor={`icp-${key}`}
              className="text-xs"
              style={{ color: '#71717a' }}
            >
              {label}
            </label>
            <input
              id={`icp-${key}`}
              value={(icp[key] as string) || ''}
              onChange={e => onChange({ ...icp, [key]: e.target.value })}
              placeholder={placeholder}
              className="w-full text-xs px-2.5 py-2 rounded-lg outline-none transition-colors"
              style={{
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)',
                color: '#e4e4e7',
                fontFamily: 'var(--font-display)',
              }}
              onFocus={e => (e.target.style.borderColor = 'rgba(16,185,129,0.4)')}
              onBlur={e => (e.target.style.borderColor = 'rgba(255,255,255,0.08)')}
            />
          </div>
        ))}
      </div>

      <div className="mt-3 flex justify-end">
        <button
          className="btn-primary flex items-center gap-1.5 text-xs px-4 py-2"
          onClick={onScan}
          disabled={loading}
          id="btn-update-icp"
        >
          <MagnifyingGlass size={13} weight="bold" />
          {loading ? 'Scanning...' : 'Update ICP & Scan Leads'}
        </button>
      </div>
    </div>
  );
}
