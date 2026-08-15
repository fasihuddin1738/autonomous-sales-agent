'use client';
import { useState, useEffect, useCallback } from 'react';
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

function addLog(logs: AgentLogEntry[], message: string): AgentLogEntry[] {
  const ts = new Date().toLocaleTimeString('en-US', { hour12: false });
  return [...logs, { timestamp: ts, message }];
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

  const log = useCallback((msg: string) => {
    setLogs(prev => addLog(prev, msg));
    setAgentStatus(msg);
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

  // Seed mock data
  const handleSeedData = async () => {
    log('Seeding mock leads into database...');
    setLoading(true);
    try {
      const res = await api.seedMockLeads();
      log(`Seeded ${res.seeded} mock leads. Refreshing board...`);
      await fetchLeads();
    } catch (e) {
      log(`Seed failed: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  // Full autonomous pipeline
  const handleLaunch = async () => {
    setLoading(true);
    log(`Launching autonomous pipeline — ${icp.target_industry} in ${icp.target_location}...`);
    try {
      log('Step 1/2: Discovering leads via NexaFlow discovery engine...');
      const discovered = await api.discoverLeads({ ...icp, max_results_per_query: 5 });
      log(`Found ${discovered.count} raw leads. Starting deep research & qualification...`);

      log('Step 2/2: Processing batch: research → qualify → service match → decision-maker ID...');
      const processed = await api.processBatch(discovered.leads, icp);
      log(`Pipeline complete. ${processed.qualified}/${processed.processed} leads qualified.`);

      await fetchLeads();
    } catch (e) {
      log(`Pipeline error: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  // Follow-up scan
  const handleScanFollowUps = async () => {
    log('Scanning for due follow-ups...');
    try {
      const res = await api.scanFollowUps(dryRun);
      log(`Follow-up scan done. ${res.follow_ups_sent.length} follow-up(s) sent.`);
      await fetchLeads();
    } catch (e) {
      log(`Follow-up scan failed: ${(e as Error).message}`);
    }
  };

  // Reset
  const handleReset = () => {
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
    setLoading(true);
    log(`Updating ICP and scanning for leads: ${icp.target_industry}, ${icp.target_location}...`);
    try {
      const discovered = await api.discoverLeads({ ...icp, max_results_per_query: 3 });
      log(`Discovered ${discovered.count} leads. Running research batch...`);
      const processed = await api.processBatch(discovered.leads, icp);
      log(`ICP scan complete: ${processed.qualified}/${processed.processed} qualified.`);
      await fetchLeads();
    } catch (e) {
      log(`ICP scan failed: ${(e as Error).message}`);
    } finally {
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
