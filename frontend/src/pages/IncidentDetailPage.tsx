import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import EmptyState from '../components/common/EmptyState'
import ErrorMessage from '../components/common/ErrorMessage'
import SeverityBadge from '../components/common/SeverityBadge'
import Spinner from '../components/common/Spinner'
import StatusBadge from '../components/common/StatusBadge'
import { useToast } from '../components/common/Toast'
import InvestigationPanel from '../components/incidents/InvestigationPanel'
import RcaPanel from '../components/incidents/RcaPanel'
import { useAuth } from '../context/AuthContext'
import { incidentService } from '../services/incidentService'
import { reportService } from '../services/knowledgeService'
import type { IncidentDetail, IncidentEvent, IncidentStatus, Severity } from '../types/incidents'
import { getErrorMessage } from '../utils/errors'
import { formatDate } from '../utils/format'

const NEXT_STATUS: Record<IncidentStatus, IncidentStatus[]> = {
  OPEN: ['INVESTIGATING', 'MITIGATED', 'RESOLVED'],
  INVESTIGATING: ['OPEN', 'MITIGATED', 'RESOLVED'],
  MITIGATED: ['INVESTIGATING', 'RESOLVED'],
  RESOLVED: ['OPEN', 'INVESTIGATING'],
}

export default function IncidentDetailPage() {
  const id = Number(useParams().id)
  const { user } = useAuth()
  const { notify } = useToast()
  const [incident, setIncident] = useState<IncidentDetail | null>(null)
  const [events, setEvents] = useState<IncidentEvent[]>([])
  const [eventFilter, setEventFilter] = useState('')
  const [note, setNote] = useState('')
  const [resolution, setResolution] = useState('')
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const [detail, timeline] = await Promise.all([incidentService.get(id), incidentService.timeline(id, eventFilter ? [eventFilter] : undefined)])
      setIncident(detail); setEvents(timeline); setResolution(detail.resolution_notes ?? ''); setError(null)
    } catch (e) {
      setError(getErrorMessage(e))
    }
  }, [id, eventFilter])
  useEffect(() => { void load() }, [load])

  const act = async (fn: () => Promise<unknown>, success: string) => {
    try { await fn(); notify('success', success); await load() } catch (e) { notify('error', getErrorMessage(e)) }
  }
  const submitNote = async (e: FormEvent) => {
    e.preventDefault()
    if (!note.trim()) return
    await act(() => incidentService.addNote(id, note.trim()), 'Note added')
    setNote('')
  }

  if (error && !incident) return <ErrorMessage message={error} />
  if (!incident) return <Spinner />
  const eventTypes = Array.from(new Set(events.map((e) => e.event_type)))

  return (
    <section className="space-y-6">
      <Link to="/incidents" className="text-sm text-blue-600 hover:underline">← Back to incidents</Link>
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">{incident.public_id}: {incident.title}</h1>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <SeverityBadge value={incident.severity} /><StatusBadge value={incident.status} />
          <span>Service: {incident.service}</span><span>Detected {formatDate(incident.detection_time)}</span>
          <span>First {formatDate(incident.first_occurrence)} · Last {formatDate(incident.last_occurrence)}</span>
          <span>Assigned: {incident.assigned_to ?? 'unassigned'}</span>
        </div>
        <p className="max-w-3xl text-sm text-slate-700">{incident.description || 'No description.'}</p>
      </header>

      <div className="grid gap-4 lg:grid-cols-3">
        <section className="rounded-lg border bg-white p-4 text-sm">
          <h2 className="mb-2 font-medium">Severity explanation (rule-based)</h2>
          <ul className="list-disc pl-5">{incident.severity_reasons.map((r) => <li key={r}>{r}</li>)}</ul>
          <label className="mt-3 block">Change severity
            <select aria-label="Change severity" value={incident.severity} onChange={(e) => void act(() => incidentService.update(id, { severity: e.target.value as Severity }), 'Severity updated')} className="ml-2 rounded border px-2 py-1">
              {['P1', 'P2', 'P3', 'P4'].map((s) => <option key={s}>{s}</option>)}
            </select>
          </label>
        </section>
        <section className="rounded-lg border bg-white p-4 text-sm">
          <h2 className="mb-2 font-medium">Status and assignment</h2>
          <div className="flex flex-wrap gap-2">
            {NEXT_STATUS[incident.status].map((s) => (
              <button key={s} type="button" onClick={() => void act(() => incidentService.update(id, { status: s }), `Status set to ${s}`)} className="rounded border px-3 py-1 hover:bg-slate-100">Mark {s}</button>
            ))}
          </div>
          <button type="button" className="mt-3 rounded border px-3 py-1 hover:bg-slate-100"
            onClick={() => void act(() => incidentService.update(id, { assigned_user_id: incident.assigned_user_id ? null : user!.id }), incident.assigned_user_id ? 'Unassigned' : 'Assigned to you')}>
            {incident.assigned_user_id ? 'Unassign' : 'Assign to me'}
          </button>
          <label className="mt-3 block">Resolution notes
            <textarea value={resolution} onChange={(e) => setResolution(e.target.value)} rows={3} className="mt-1 w-full rounded border px-2 py-1" />
          </label>
          <button type="button" onClick={() => void act(() => incidentService.update(id, { resolution_notes: resolution }), 'Resolution notes saved')} className="mt-1 rounded border px-3 py-1">Save notes</button>
        </section>
        <section className="rounded-lg border bg-white p-4 text-sm">
          <h2 className="mb-2 font-medium">Reports</h2>
          <p className="mb-2 text-slate-600">{incident.linked_log_count} error log entries linked.</p>
          <div className="flex gap-2">
            {(['pdf', 'csv', 'json'] as const).map((f) => (
              <button key={f} type="button" className="rounded border px-3 py-1 uppercase hover:bg-slate-100"
                onClick={() => void act(async () => reportService.download(await reportService.generate(id, f)), `${f.toUpperCase()} report generated`)}>{f}</button>
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-lg border bg-white p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-medium">Timeline</h2>
          <select aria-label="Filter timeline" value={eventFilter} onChange={(e) => setEventFilter(e.target.value)} className="rounded border px-2 py-1 text-sm">
            <option value="">All events</option>{eventTypes.map((t) => <option key={t}>{t}</option>)}
            {eventFilter && !eventTypes.includes(eventFilter) && <option>{eventFilter}</option>}
          </select>
        </div>
        {events.length === 0 ? <EmptyState message="No timeline events." /> : (
          <ol className="space-y-2 border-l-2 border-blue-200 pl-4 text-sm">
            {events.map((e) => (
              <li key={e.id}><span className="font-mono text-xs text-slate-500">{formatDate(e.timestamp)}</span>{' '}
                <span className="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-800">{e.event_type}</span> {e.description}</li>
            ))}
          </ol>
        )}
      </section>

      <section className="rounded-lg border bg-white p-4 text-sm">
        <h2 className="mb-2 font-medium">Related incidents</h2>
        <p className="mb-2 text-xs text-slate-500">Similarity indicates comparable symptoms, not a confirmed common root cause.</p>
        {incident.related.length === 0 ? <EmptyState message="No similar incidents found." /> : (
          <ul className="space-y-1">{incident.related.map((r) => (
            <li key={r.similar_incident_id}><Link to={`/incidents/${r.similar_incident_pk}`} className="text-blue-600 hover:underline">{r.similar_incident_id} {r.title}</Link>
              {' '}similarity {r.similarity_score.toFixed(2)}{r.shared_services.length > 0 && ` · shared services: ${r.shared_services.join(', ')}`}</li>
          ))}</ul>
        )}
      </section>

      <RcaPanel summary={incident.anomaly_summary} />

      <InvestigationPanel incident={incident} onDone={() => void load()} />

      <section className="rounded-lg border bg-white p-4 text-sm">
        <h2 className="mb-2 font-medium">Human investigation notes</h2>
        {incident.notes.length === 0 ? <EmptyState message="No notes yet." /> : (
          <ul className="mb-3 space-y-2">{incident.notes.map((n) => <li key={n.id}><span className="text-xs text-slate-500">{formatDate(n.created_at)} · {n.author_name ?? 'unknown'}</span><br />{n.content}</li>)}</ul>
        )}
        <form onSubmit={submitNote} className="flex gap-2">
          <input aria-label="New note" value={note} onChange={(e) => setNote(e.target.value)} maxLength={5000} placeholder="Add an investigation note" className="flex-1 rounded border px-2 py-1" />
          <button type="submit" className="rounded bg-blue-600 px-3 py-1 text-white">Add note</button>
        </form>
      </section>
    </section>
  )
}
