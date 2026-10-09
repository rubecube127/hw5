import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api'
import type { AgentEvent, Finding, PaymentProposal, Ticket } from './types'

const AGENTS = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

function eventText(event: AgentEvent) {
  const details = event.details as { task?: string; summary?: string; target?: string; tool?: string }
  if (details.summary) return details.summary
  if (details.target) return `Asked ${details.target.replace('_', ' ')} to help with this ticket.`
  if (details.tool) {
    const plainLanguage: Record<string, string> = {
      get_ticket: 'Reviewed the ticket details.', check_inventory: 'Checked the requested item’s stock.',
      get_invoice_vendor: 'Reviewed the supplier invoice and lead time.', get_lease_rent_status: 'Reviewed the lease and rent timing.',
      get_pricing: 'Reviewed product cost and price.', get_cash_status: 'Checked whether enough cash is available.',
      get_vendor_open_invoices: 'Checked whether the supplier has unpaid invoices.', list_open_tickets: 'Reviewed the open work board.',
    }
    return plainLanguage[details.tool] ?? 'Reviewed the records needed for this ticket.'
  }
  const actions: Record<string, string> = {
    loop_start: 'Started reviewing the ticket.', loop_complete: 'Finished a review and shared findings.',
    payment_executed: 'Recorded the approved payment.', ticket_resolved: 'Marked the ticket resolved.',
    approval_denied: 'Recorded that the payment was denied.',
  }
  return actions[event.action] ?? 'Updated the ticket work.'
}

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [events, setEvents] = useState<AgentEvent[]>([])
  const requestedTicket = Number(new URLSearchParams(window.location.search).get('ticket'))
  const [selected, setSelected] = useState<number | null>(Number.isInteger(requestedTicket) && requestedTicket > 0 ? requestedTicket : null)
  const [running, setRunning] = useState(false)
  const [finding, setFinding] = useState<Finding | null>(null)
  const [cash, setCash] = useState<number | null>(null)
  const [message, setMessage] = useState('')
  const [approval, setApproval] = useState<PaymentProposal | null>(null)
  const [approvalOpen, setApprovalOpen] = useState(false)
  const lastResetMarker = useRef<string | null>(null)

  const refresh = async () => {
    try {
      const [nextTickets, nextCash, nextEvents] = await Promise.all([api.tickets(), api.cash(), api.events()])
      const latestReset = nextEvents.map(event => event.action).lastIndexOf('system_reset')
      setTickets(nextTickets); setCash(nextCash.balance); setEvents(latestReset >= 0 ? nextEvents.slice(latestReset + 1) : nextEvents)
      const resetMarker = latestReset >= 0 ? nextEvents[latestReset].timestamp : null
      if (resetMarker && resetMarker !== lastResetMarker.current) { lastResetMarker.current = resetMarker; setFinding(null); setApproval(null); setApprovalOpen(false) }
      const pending = (await Promise.all(nextTickets.filter(ticket => ticket.state === 'open').map(async ticket => ({ ticket, proposal: await api.approvalForTicket(ticket.id) })))).find(item => item.proposal)
      if (pending?.proposal) { setSelected(pending.ticket.id); setApproval(pending.proposal); setApprovalOpen(true) }
      setSelected(current => current ?? nextTickets[0]?.id ?? null)
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Cannot reach backend') }
  }
  useEffect(() => { void refresh(); const id = window.setInterval(() => void refresh(), 1800); return () => window.clearInterval(id) }, [])

  const active = tickets.find(ticket => ticket.id === selected) ?? null
  const ticketEvents = useMemo(() => {
    const scoped = events.filter(event => event.ticket_id === selected)
    const latestRunId = scoped.at(-1)?.run_id
    return latestRunId ? scoped.filter(event => event.run_id === latestRunId) : []
  }, [events, selected])
  const savedFinding = useMemo(() => {
    const completed = [...ticketEvents].reverse().find(event => event.agent === 'boss' && event.action === 'loop_complete')
    const details = completed?.details as Partial<Finding> | undefined
    return details?.summary ? details as Finding : null
  }, [ticketEvents])
  const displayFinding = finding ?? savedFinding
  const emailDraft = useMemo(() => {
    const completed = [...ticketEvents].reverse().find(event => event.agent === 'customer_service' && event.action === 'loop_complete')
    const details = completed?.details as Partial<Finding> | undefined
    return details?.draft_email ?? null
  }, [ticketEvents])

  useEffect(() => {
    if (!active || active.state === 'resolved') { setApproval(null); return }
    void api.approvalForTicket(active.id).then(setApproval).catch(() => setApproval(null))
  }, [active?.id, active?.state])

  const run = async () => {
    if (!active) return
    setRunning(true); setMessage('Agents are reviewing the ticket…'); setFinding(null)
    try {
      const result = await api.run(active.id)
      setFinding(result.finding); setApproval(result.approval_request); setApprovalOpen(Boolean(result.approval_request))
      if (result.approval_request) setSelected(result.approval_request.ticket_id)
      setMessage(result.approval_request ? 'A payment is ready for your approval.' : `Ticket ${active.id} resolved`)
      await refresh()
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Run failed') }
    finally { setRunning(false) }
  }

  const approve = async () => {
    if (!approval) return
    try {
      await api.approve({ approved: true, amount: approval.amount, kind: approval.kind, ref_id: approval.ref_id, ticket_id: approval.ticket_id })
      setApproval(null); setApprovalOpen(false); setMessage('Approved payment recorded and ticket resolved.'); await refresh()
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Approval failed') }
  }

  const deny = async () => {
    if (!approval) return
    await api.deny(approval.ticket_id)
    setApproval(null); setApprovalOpen(false); setMessage('Approval denied. The ticket remains open.'); await refresh()
  }

  return <main className="app-shell">
    <div className="cork-sprinkles" aria-hidden="true"><span className="sprinkle-one">♥</span><span className="sprinkle-two">✿</span><span className="sprinkle-three">♡</span><span className="sprinkle-four">✿</span><span className="sprinkle-five">♥</span><span className="sprinkle-six">✿</span></div>
    <header className="masthead"><div className="masthead-copy"><p className="eyebrow">YALE CAMPUS CUSTOMS</p><h1>Operations Bulletin Board</h1><p className="masthead-note">Shop desk · agent coordination · human approval</p></div><div className="seal" aria-hidden="true">YC</div><div className="cash-card"><span>Checking balance</span><strong>{cash === null ? '—' : `$${cash.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}</strong></div></header>
    {message && <p className="notice">{message}</p>}
    <section className="board">
      <aside className="ticket-rail"><h2>Tickets</h2>{tickets.map(ticket => <button key={ticket.id} onClick={() => { setSelected(ticket.id); setFinding(null) }} className={`ticket-card ${ticket.state} ${ticket.id === selected ? 'selected' : ''}`}><span className="pin"/><small>#{ticket.id} · {ticket.state}</small><b>{ticket.subject}</b><span>{ticket.requester}</span></button>)}</aside>
      <section className="ticket-detail">
        <div className="tape tape-left" aria-hidden="true" /><div className="tape tape-right" aria-hidden="true" />
        {active ? <><div className="ticket-heading"><div><p className={`status ${active.state}`}>{active.state}</p><h2>#{active.id} · {active.subject}</h2><p>{active.notes}</p></div><button className="run-button" disabled={running || active.state === 'resolved'} onClick={() => void run()}>{running ? 'Team running…' : active.state === 'resolved' ? 'Resolved' : 'Start agent team'}</button></div>
        {approval && <section className="approval-alert"><div><p className="approval-kicker">Action needed · human decision</p><h3>{approval.label} — ${approval.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</h3><p>Ticket #{approval.ticket_id} will remain open until a person approves or denies this outgoing payment.</p></div><button onClick={() => setApprovalOpen(true)}>Review payment</button></section>}
        <div className="grid"><article className="paper summary"><h3>Agent summary</h3>{displayFinding ? <><p>{displayFinding.summary}</p><ul>{displayFinding.facts.map(fact => <li key={fact}>{fact}</li>)}</ul>{displayFinding.blockers.length > 0 && <p><b>Blockers:</b> {displayFinding.blockers.join('; ')}</p>}</> : <p>Start the team to receive a concise Boss summary for this ticket.</p>}</article>
        <article className="paper activity"><h3>Live activity</h3><div className="activity-log">{ticketEvents.length ? ticketEvents.map((event, index) => <p key={`${event.timestamp}-${index}`}><b>{event.agent}</b> <span>{eventText(event)}</span></p>) : <p>Waiting for agent events…</p>}</div></article></div>
        {emailDraft && <article className="paper email-draft"><p className="approval-kicker">Mock email · not sent</p><h3>Customer Service draft</h3><pre>{emailDraft}</pre><p className="draft-note">This is a display-only draft for human review. No email was sent.</p></article>}
        <div className="agent-row">{AGENTS.map(agent => <span key={agent} className={ticketEvents.some(event => event.agent === agent) ? 'active-agent' : ''}>{agent.replace('_', ' ')}</span>)}</div>
        <section className="approval paper"><div><h3>Human approval desk</h3><p>When a payment is needed, its details appear here for a one-click decision.</p></div></section>
        {approval && approvalOpen && <div className="approval-overlay" role="dialog" aria-modal="true" aria-label="Payment approval"><div className="approval-modal"><p className="approval-kicker">Human approval required</p><h3>{approval.label}</h3><p>Ticket #{approval.ticket_id}{approval.ref_id ? ` · Reference ${approval.ref_id}` : ''}</p><strong>${approval.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</strong><p className="approval-note">This is an outgoing payment. The ticket stays open until you decide. Approving will reduce the checking balance.</p><div className="approval-actions"><button className="deny" onClick={() => void deny()}>Deny — keep ticket open</button><button onClick={() => void approve()}>Approve ${approval.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</button></div></div></div>}
        </> : <p>Select a ticket to begin.</p>}
      </section>
    </section>
  </main>
}
