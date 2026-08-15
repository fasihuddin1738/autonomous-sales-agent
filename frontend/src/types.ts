// ─── types.ts ───────────────────────────────────────────────────────────────
// Single source of truth for all data shapes mirroring shared/schema.py

export type PipelineStage =
  | 'Discovered'
  | 'Potential'
  | 'Researching'
  | 'Qualified'
  | 'Contacted'
  | 'Interested'
  | 'Meeting Scheduled'
  | 'Converted'
  | 'Not Qualified'
  | 'Not Interested'
  | 'Do Not Contact';

export type OutreachStatus = 'Drafted' | 'Sent' | 'Replied' | 'Bounced' | 'Followed Up';

export type ResponseClassification =
  | 'Positive / Interested'
  | 'Meeting Requested'
  | 'Question'
  | 'Pricing Objection'
  | 'Technical Objection'
  | 'Not Interested'
  | 'Not Now'
  | 'Wrong Person / Referral'
  | 'Other';

export interface DecisionMaker {
  name: string | null;
  role: string;
  email: string | null;
  linkedin?: string | null;
  priority: number;
}

export interface OutreachMessage {
  id: string;
  contact: DecisionMaker;
  subject: string;
  body: string;
  evidence_used: string[];
  status: OutreachStatus;
  sent_at?: string | null;
  reply_text?: string | null;
  reply_classification?: ResponseClassification | null;
  follow_up_count: number;
  next_follow_up_at?: string | null;
}

export interface ResearchFindings {
  website?: string | null;
  employees_estimate?: string | null;
  key_departments: string[];
  recent_news: string[];
  funding_signal?: string | null;
  tech_stack: string[];
  buying_signals: string[];
  raw_notes?: string | null;
}

export interface Qualification {
  score: number;
  reasoning: string;
  factors: string[];
  is_qualified: boolean;
}

export interface Meeting {
  scheduled_time?: string | null;
  meeting_link?: string | null;
  briefing?: string | null;
  admin_reminder_sent: boolean;
}

export interface Lead {
  id: string;
  company_name: string;
  source?: string | null;
  icp_fit_notes?: string | null;
  research: ResearchFindings;
  qualification?: Qualification | null;
  recommended_service?: string | null;
  decision_makers: DecisionMaker[];
  pipeline_stage: PipelineStage;
  outreach: OutreachMessage[];
  meeting?: Meeting | null;
  memory_log: string[];
  created_at: string;
  updated_at: string;
}

export interface ICP {
  target_location: string;
  target_industry: string;
  company_size?: string;
  special_focus?: string;
}

export interface AgentLogEntry {
  timestamp: string;
  message: string;
}
