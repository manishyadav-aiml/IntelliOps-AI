import { Plus } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import DataTable from '../components/common/DataTable'
import EmptyState from '../components/common/EmptyState'
import ErrorMessage from '../components/common/ErrorMessage'
import Pagination from '../components/common/Pagination'
import SearchBar from '../components/common/SearchBar'
import SeverityBadge from '../components/common/SeverityBadge'
import Spinner from '../components/common/Spinner'
import StatusBadge from '../components/common/StatusBadge'
import { useToast } from '../components/common/Toast'
import { incidentService } from '../services/incidentService'
import type { Incident, Severity } from '../types/incidents'
import type { Page } from '../types/logs'
import { getErrorMessage } from '../utils/errors'
import { formatDate } from '../utils/format'

export default function IncidentsPage() {
  const { notify } = useToast()
  const [data, setData] = useState<Page<Incident> | null>(null)
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [severity, setSeverity] = useState('')
  const [q, setQ] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState<{ title: string; service: string; severity: Severity; description: string }>({ title: '', service: '', severity: 'P3', description: '' })

  const load = useCallback(async () => {
    try {
      setData(await incidentService.list({ page, status: status || undefined, severity: severity || undefined, q: q || undefined }))
      setError(null)
    } catch (e) {
      setError(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }, [page, status, severity, q])
  useEffect(() => { void load() }, [load])

  const create = async (event: FormEvent) => {
    event.preventDefault()
    try {
      const created = await incidentService.create({ title: form.title, service: form.service || undefined, severity: form.severity, description: form.description })
      notify('success', `Created ${created.public_id}`)
      setCreating(false); setForm({ title: '', service: '', severity: 'P3', description: '' })
      await load()
    } catch (e) {
      notify('error', getErrorMessage(e))
    }
  }

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Incidents</h1>
        <button type="button" onClick={() => setCreating(!creating)} className="flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-sm text-white">
          <Plus className="h-4 w-4" aria-hidden="true" /> New incident
        </button>
      </div>
      {creating && (
        <form onSubmit={create} className="grid gap-3 rounded-lg border bg-white p-4 md:grid-cols-2" aria-label="Create incident">
          <label className="text-sm">Title<input required maxLength={200} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="mt-1 w-full rounded border px-2 py-1" /></label>
          <label className="text-sm">Service<input value={form.service} onChange={(e) => setForm({ ...form, service: e.target.value })} className="mt-1 w-full rounded border px-2 py-1" /></label>
          <label className="text-sm">Severity
            <select value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value as Severity })} className="mt-1 w-full rounded border px-2 py-1">
              {['P1', 'P2', 'P3', 'P4'].map((s) => <option key={s}>{s}</option>)}
            </select></label>
          <label className="text-sm md:col-span-2">Description<textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="mt-1 w-full rounded border px-2 py-1" rows={3} /></label>
          <div className="md:col-span-2"><button type="submit" className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white">Create</button></div>
        </form>
      )}
      <div className="flex flex-wrap gap-3">
        <SearchBar value={q} onChange={(v) => { setQ(v); setPage(1) }} placeholder="Search title" label="Search incidents" />
        <select aria-label="Filter by status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }} className="rounded border px-2 py-1.5 text-sm">
          <option value="">All statuses</option>{['OPEN', 'INVESTIGATING', 'MITIGATED', 'RESOLVED'].map((s) => <option key={s}>{s}</option>)}
        </select>
        <select aria-label="Filter by severity" value={severity} onChange={(e) => { setSeverity(e.target.value); setPage(1) }} className="rounded border px-2 py-1.5 text-sm">
          <option value="">All severities</option>{['P1', 'P2', 'P3', 'P4'].map((s) => <option key={s}>{s}</option>)}
        </select>
      </div>
      {error && <ErrorMessage message={error} />}
      {loading ? <Spinner /> : data && data.items.length === 0 ? (
        <EmptyState message="No incidents match. Incidents appear after anomaly detection finds problems, or create one manually." />
      ) : data && (
        <>
          <DataTable<Incident> rowKey={(i) => i.id} rows={data.items} columns={[
            { header: 'Incident', cell: (i) => <Link to={`/incidents/${i.id}`} className="text-blue-600 hover:underline">{i.public_id} {i.title}</Link> },
            { header: 'Service', cell: (i) => i.service },
            { header: 'Severity', cell: (i) => <SeverityBadge value={i.severity} /> },
            { header: 'Status', cell: (i) => <StatusBadge value={i.status} /> },
            { header: 'Detected', cell: (i) => formatDate(i.detection_time) },
          ]} />
          <Pagination page={data.page} pageSize={data.page_size} total={data.total} onChange={setPage} />
        </>
      )}
    </section>
  )
}
