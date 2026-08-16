import { useState, useEffect, useCallback, useRef } from 'react';
import { AnimatePresence } from 'framer-motion';
import './index.css';
import GridBackground from './components/GridBackground';
import Header from './components/Header';
import AgentReasoningPanel from './components/AgentReasoningPanel';
import ICPPanel from './components/ICPPanel';
import KPIStrip from './components/KPIStrip';
import KanbanBoard from './components/KanbanBoard';
import LeadDrawer from './components/LeadDrawer';
import type { Lead, ICP, AgentLogEntry } from './types';
import * as api from './api';

const DEFAULT_ICP: ICP = {
  target_location: 'Karachi, Pakistan',
  target_industry: 'E-commerce',
  company_size: '50-300 employees',
  special_focus: 'High WhatsApp inquiry volume',
};

function addLog(logs: AgentLogEntry[], message: string, kind: AgentLogEntry['kind'] = 'info'): AgentLogEntry[] {
  const ts = new Date().toLocaleTimeString('en-US', { hour12: false });
  return [...logs, { timestamp: ts, message, kind }];
}

export default function App() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [icp, setIcp] = useState<ICP>(DEFAULT_ICP);
  const [mockMode, setMockMode] = useState(true);
  const [dryRun, setDryRun] = useState(true);
  const [loading, setLoading] = useState(false);
  const [agentStatus, setAgentStatus] = useState('Idle — waiting for pipeline launch');
  const [logs, setLogs] = useState<AgentLogEntry[]>([]);
  const [showNegative, setShowNegative] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Info log — appears in reasoning stream AND status bar
  const log = useCallback((msg: string) => {
    setLogs(prev => addLog(prev, msg, 'info'));
    setAgentStatus(msg);
  }, []);

  // Error log — appears ONLY in status bar, never in the reasoning stream
  const logError = useCallback((msg: string) => {
    setAgentStatus(`⚠ ${msg}`);
  }, []);

  // Fetch all leads
  const fetchLeads = useCallback(async () => {
    try {
      const data = await api.getLeads();
      setLeads(data);
    } catch {
      // Backend may not be running yet
    }
  }, []);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  // Stop running pipeline
  const handleStop = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    // Tell the backend to skip any remaining steps (fire-and-forget)
    api.cancelPipeline().catch(() => {});
    setLoading(false);
    log('Pipeline execution stopped by user.');
  }, [log]);

  // Seed mock data
  const handleSeedData = async () => {
    log('Seeding mock leads into database...');
    setLoading(true);
    try {
      const res = await api.seedMockLeads();
      log(`Seeded ${res.seeded} mock leads successfully. Refreshing board...`);
      await fetchLeads();
    } catch (e) {
      logError(`Seed failed: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  // Full autonomous pipeline
  const handleLaunch = async () => {
    const controller = new AbortController();
    abortControllerRef.current = controller;
    setLoading(true);
    try {
      await api.resetPipeline().catch(() => {});

      if (mockMode) {
        // ── Mock mode: skip real discovery & LLM calls entirely ──────────────
        log('Mock mode ON — skipping live discovery. Loading pre-built mock leads...');
        const res = await api.seedMockLeads();
        log(`Seeded ${res.seeded} mock leads into the pipeline. Board updated.`);
        await fetchLeads();
        return;
      }

      // ── Live mode: real discovery + research pipeline ─────────────────────
      log(`Launching autonomous pipeline — ${icp.target_industry} in ${icp.target_location}...`);
      log(`ICP target: ${icp.target_industry} companies, ${icp.target_location}${icp.company_size ? `, ${icp.company_size}` : ''}`);
      log('Step 1/2: Running discovery queries via NexaFlow search engine...');
      const discovered = await api.discoverLeads(
        { ...icp, max_results_per_query: 5 },
        controller.signal
      );
      // If the proxy detected a disconnect, bail out cleanly
      if (discovered.cancelled) {
        log('Pipeline cancelled by user.');
        return;
      }
      const rawCount = discovered.leads.length;
      log(`Discovery complete. Found ${rawCount} candidate${rawCount !== 1 ? 's' : ''} that passed quality filter.`);
      if (rawCount > 0) {
        log(`Candidates: ${discovered.leads.slice(0, 5).map(l => l.company_name).join(', ')}${rawCount > 5 ? ` +${rawCount - 5} more` : ''}.`);
      }

      if (controller.signal.aborted) {
        log('Pipeline cancelled before research step.');
        return;
      }

      log('Step 2/2: Running deep research pipeline: tech stack → buying signals → qualification scoring → service match → decision-maker ID...');
      const processed = await api.processBatch(discovered.leads, icp, controller.signal);
      const notQualified = processed.processed - processed.qualified;
      log(`Research & qualification complete.`);
      log(`Qualified: ${processed.qualified}/${processed.processed} leads. Filtered out: ${notQualified} below threshold.`);
      if (processed.qualified > 0) {
        const qualifiedLeads = processed.leads.filter(l => l.qualification?.is_qualified);
        qualifiedLeads.slice(0, 3).forEach(l => {
          log(`  ✓ ${l.company_name} — score ${l.qualification?.score ?? '?'}/100, recommended: ${l.recommended_service ?? 'TBD'}`);
        });
      }
      log('Pipeline complete. Board updated.');
      await fetchLeads();
    } catch (e: any) {
      if (e?.name === 'AbortError' || controller.signal.aborted) {
        log('Pipeline cancelled by user.');
      } else {
        logError(`Pipeline error: ${e?.message || e}`);
      }
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
      setLoading(false);
    }
  };

  // Follow-up scan
  const handleScanFollowUps = async () => {
    log('Scanning all leads for due follow-ups...');
    try {
      const res = await api.scanFollowUps(dryRun);
      if (res.follow_ups_sent.length === 0) {
        log('Follow-up scan complete. No follow-ups due at this time.');
      } else {
        log(`Follow-up scan complete. ${res.follow_ups_sent.length} follow-up(s) dispatched${dryRun ? ' (dry-run)' : ''}.`);
        res.follow_ups_sent.forEach(f => log(`  → Follow-up sent to: ${f.company_name}`));
      }
      await fetchLeads();
    } catch (e) {
      logError(`Follow-up scan failed: ${(e as Error).message}`);
    }
  };

  // Reset
  const handleReset = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setLoading(false);
    setLeads([]);
    setLogs([]);
    setAgentStatus('Idle — session reset');
    setSelectedLead(null);
  };

  // Lead update from drawer actions
  const handleLeadUpdated = useCallback((updated: Lead) => {
    setLeads(prev => prev.map(l => l.id === updated.id ? updated : l));
    setSelectedLead(updated);
    log(`Updated lead: ${updated.company_name} → ${updated.pipeline_stage}`);
  }, [log]);

  // ICP scan
  const handleICPScan = async () => {
    const controller = new AbortController();
    abortControllerRef.current = controller;
    setLoading(true);
    try {
      await api.resetPipeline().catch(() => {});

      if (mockMode) {
        // ── Mock mode: skip real discovery & LLM calls entirely ──────────────
        log('Mock mode ON — skipping live discovery. Loading pre-built mock leads...');
        const res = await api.seedMockLeads();
        log(`Seeded ${res.seeded} mock leads into the pipeline. Board updated.`);
        await fetchLeads();
        return;
      }

      // ── Live mode ─────────────────────────────────────────────────────────
      log(`ICP scan started — ${icp.target_industry} in ${icp.target_location}...`);
      log(`Parameters: size=${icp.company_size ?? 'any'}, focus="${icp.special_focus ?? 'none'}".`);
      log('Running discovery queries...');
      const discovered = await api.discoverLeads(
        { ...icp, max_results_per_query: 3 },
        controller.signal
      );
      // If the proxy detected a disconnect, bail out cleanly
      if (discovered.cancelled) {
        log('ICP scan cancelled by user.');
        return;
      }
      const rawCount = discovered.leads.length;
      log(`Found ${rawCount} candidate${rawCount !== 1 ? 's' : ''} that passed quality filter.`);
      if (rawCount > 0) {
        log(`Candidates: ${discovered.leads.slice(0, 4).map(l => l.company_name).join(', ')}${rawCount > 4 ? ` +${rawCount - 4} more` : ''}.`);
      }

      if (controller.signal.aborted) {
        log('ICP scan cancelled before research step.');
        return;
      }

      log('Running research & qualification batch...');
      const processed = await api.processBatch(discovered.leads, icp, controller.signal);
      log(`ICP scan complete — ${processed.qualified}/${processed.processed} leads qualified.`);
      await fetchLeads();
    } catch (e: any) {
      if (e?.name === 'AbortError' || controller.signal.aborted) {
        log('ICP scan cancelled by user.');
      } else {
        logError(`ICP scan failed: ${e?.message || e}`);
      }
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[100dvh] relative" style={{ background: 'var(--bg)' }}>
      {/* Background layer */}
      <GridBackground />

      {/* Content layer */}
      <div className="relative z-10 flex flex-col min-h-[100dvh]">
        <Header
          agentStatus={agentStatus}
          mockMode={mockMode}
          dryRun={dryRun}
          onToggleMock={() => setMockMode(m => !m)}
          onToggleDryRun={() => setDryRun(d => !d)}
          onLaunch={handleLaunch}
          onStop={handleStop}
          onScanFollowUps={handleScanFollowUps}
          onSeedData={handleSeedData}
          onReset={handleReset}
          loading={loading}
        />

        <main className="flex-1 max-w-[1400px] w-full mx-auto px-4 py-5 flex flex-col gap-4">
          {/* Agent reasoning */}
          <AgentReasoningPanel logs={logs} />

          {/* ICP + KPI row */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
            <div className="lg:col-span-3">
              <ICPPanel
                icp={icp}
                onChange={setIcp}
                onScan={handleICPScan}
                loading={loading}
              />
            </div>
            <div className="lg:col-span-2">
              <KPIStrip leads={leads} />
            </div>
          </div>

          {/* Kanban pipeline */}
          <div className="flex-1">
            <div className="flex items-center justify-between mb-3">
              <h2
                className="text-xs font-semibold uppercase tracking-widest"
                style={{ color: '#52525b' }}
              >
                Pipeline Board
              </h2>
              <button
                className="btn-ghost text-xs px-3 py-1.5"
                onClick={fetchLeads}
                id="btn-refresh"
              >
                Refresh
              </button>
            </div>

            <KanbanBoard
              leads={leads}
              showNegative={showNegative}
              onToggleNegative={() => setShowNegative(v => !v)}
              onSelectLead={setSelectedLead}
            />
          </div>
        </main>
      </div>

      {/* Lead Detail Drawer */}
      <AnimatePresence>
        {selectedLead && (
          <LeadDrawer
            key={selectedLead.id}
            lead={selectedLead}
            dryRun={dryRun}
            onClose={() => setSelectedLead(null)}
            onLeadUpdated={handleLeadUpdated}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
