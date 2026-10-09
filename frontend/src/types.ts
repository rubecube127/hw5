export type Ticket = {
  id: number; type: string; requester: string; subject: string; status: string; state: 'open' | 'resolved';
  sku?: string; size?: string; qty?: number; notes?: string;
}

export type AgentEvent = {
  timestamp: string; run_id: string; step: number; agent: string; action: string;
  ticket_id?: number; details: Record<string, unknown>;
}

export type Finding = {
  agent: string; ticket_id: number; summary: string; facts: string[]; blockers: string[];
  recommended_next_step: string; requires_human_approval: boolean; delegated_to: string[];
  draft_email?: string | null;
}

export type PaymentProposal = {
  ticket_id: number; amount: number; kind: 'invoice' | 'rent' | 'purchase'; ref_id?: number; label: string;
}

export type RunResult = { finding: Finding; approval_request: PaymentProposal | null }
