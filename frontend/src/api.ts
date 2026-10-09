import type { AgentEvent, PaymentProposal, RunResult, Ticket } from './types'

const API = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { headers: { 'Content-Type': 'application/json', ...init?.headers }, ...init })
  if (!response.ok) throw new Error((await response.json().catch(() => ({ detail: response.statusText }))).detail ?? 'Request failed')
  return response.json() as Promise<T>
}

export const api = {
  tickets: () => request<Ticket[]>('/tickets'),
  cash: () => request<{ name: string; balance: number; date: string }>('/cash'),
  events: () => request<AgentEvent[]>('/events?limit=100'),
  approvalForTicket: (id: number) => request<PaymentProposal | null>(`/tickets/${id}/approval`),
  run: (id: number) => request<RunResult>(`/tickets/${id}/run`, { method: 'POST' }),
  approve: (body: { approved: boolean; amount: number; kind: 'invoice' | 'rent' | 'purchase'; ref_id?: number; ticket_id: number }) =>
    request('/approvals', { method: 'POST', body: JSON.stringify(body) }),
  deny: (ticketId: number) => request(`/approvals/deny?ticket_id=${ticketId}`, { method: 'POST' }),
}
