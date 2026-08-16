// ─── api.ts ─────────────────────────────────────────────────────────────────
// All API calls to the FastAPI backend. Proxy is configured in vite.config.ts.

import type { Lead, ICP } from './types';

const BASE = '';

async function req<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(BASE + url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── Discovery ────────────────────────────────────────────────────────────────
export const discoverLeads = (icp: ICP & { max_results_per_query?: number }, signal?: AbortSignal) =>
  req<{ count: number; leads: Lead[]; cancelled?: boolean }>('/outreach/proxy-discover', {
    method: 'POST',
    body: JSON.stringify(icp),
    signal,
  });

export const processBatch = (leads: Lead[], icp: ICP, signal?: AbortSignal) =>
  req<{ processed: number; qualified: number; leads: Lead[] }>('/research/process-batch', {
    method: 'POST',
    body: JSON.stringify({ leads, icp }),
    signal,
  });

// ── Leads ────────────────────────────────────────────────────────────────────
export const getLeads = (stage?: string) =>
  req<Lead[]>(`/outreach/leads${stage ? `?stage=${encodeURIComponent(stage)}` : ''}`);

export const getLead = (id: string) =>
  req<Lead>(`/outreach/leads/${id}`);

export const advanceStage = (id: string, stage: string, reason?: string) =>
  req<Lead>(
    `/outreach/leads/${id}/stage?target=${encodeURIComponent(stage)}${reason ? `&reason=${encodeURIComponent(reason)}` : ''}`,
    {
      method: 'POST',
    }
  );

// ── Outreach ─────────────────────────────────────────────────────────────────
export const draftEmail = (id: string, contactEmail?: string) =>
  req<Lead>(`/outreach/leads/${id}/draft-email${contactEmail ? `?contact_email=${contactEmail}` : ''}`, {
    method: 'POST',
  });

export const sendEmail = (id: string, outreachMessageId: string, dryRun: boolean) =>
  req<Lead>(`/outreach/leads/${id}/send-email`, {
    method: 'POST',
    body: JSON.stringify({ outreach_message_id: outreachMessageId, dry_run: dryRun }),
  });

export const submitReply = (id: string, outreachMessageId: string, replyText: string) =>
  req<Lead>(`/outreach/leads/${id}/reply`, {
    method: 'POST',
    body: JSON.stringify({ outreach_message_id: outreachMessageId, reply_text: replyText }),
  });

export const runFollowUp = (id: string, dryRun: boolean) =>
  req<Lead>(`/outreach/leads/${id}/run-follow-up?dry_run=${dryRun}`, { method: 'POST' });

export const scheduleMeeting = (id: string, scheduledTime: string) =>
  req<Lead>(`/outreach/leads/${id}/schedule-meeting`, {
    method: 'POST',
    body: JSON.stringify({ scheduled_time: scheduledTime }),
  });

export const sendBriefing = (id: string, dryRun: boolean) =>
  req<Lead>(`/outreach/leads/${id}/send-briefing?dry_run=${dryRun}`, { method: 'POST' });

// ── Debug ─────────────────────────────────────────────────────────────────────
export const seedMockLeads = () =>
  req<{ seeded: number }>('/outreach/debug/seed-mock-leads', { method: 'POST' });

export const scanFollowUps = (dryRun: boolean) =>
  req<{ follow_ups_sent: { lead_id: string; company_name: string }[] }>(
    `/outreach/follow-ups/scan?dry_run=${dryRun}`,
    { method: 'POST' }
  );

export const cancelPipeline = () =>
  req<{ cancelled: boolean }>('/outreach/cancel-pipeline', { method: 'POST' });

export const resetPipeline = () =>
  req<{ reset: boolean }>('/outreach/reset-pipeline', { method: 'POST' });
