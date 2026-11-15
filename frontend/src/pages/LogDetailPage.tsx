import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import ErrorMessage from '../components/common/ErrorMessage'
import Pagination from '../components/common/Pagination'
import Spinner from '../components/common/Spinner'
import StatusBadge from '../components/common/StatusBadge'
import { logService } from '../services/logService'
import type { Facets, LogEntry, LogUpload, Page, TemplateSummary } from '../types/logs'
import { getErrorMessage } from '../utils/errors'
import { formatBytes, formatDate } from '../utils/format'

export default function LogDetailPage() {
  const logId = Number(useParams().id)
  const [upload, setUpload] = useState<LogUpload | null>(null)
  const [templates, setTemplates] = useState<TemplateSummary[]>([])
  const [facets, setFacets] = useState<Facets>({ levels: [], services: [] })
  const [entries, setEntries] = useState<Page<LogEntry> | null>(null)
  const [selected, setSelected] = useState<LogEntry | null>(null)
  const [page, setPage] = useState(1)
  const [level, setLevel] = useState('')
  const [service, setService] = useState('')
  const [templateId, setTemplateId] = useState<number | undefined>()
  const [q, setQ] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([logService.get(logId), logService.templates(logId), logService.facets(logId)])
      .then(([u, t, f]) => { setUpload(u); setTemplates(t); setFacets(f) })
      .catch((err) => setError(getErrorMessage(err)))
  }, [logId])

  useEffect(() => {
    logService
      .entries(logId, { page, level: level || undefined, service: service || undefined, templateId, q: q || undefined })
      .then((d) => { setEntries(d); setError(null) })
      .catch((err) => setError(getErrorMessage(err)))
  }, [logId, page, level, service, templateId, q])

  const reset = (fn: () => void) => { fn(); setPage(1) }

  if (error && !upload) return <ErrorMessage message={error} />
  if (!upload) return <Spinner />

  return (
    <section className="space-y-6">
      <Link to="/logs" className="text-sm text-blue-600 hover:underline">← Back to log files</Link>
      <header>
        <h1 className="text-2xl font-semibold">{upload.filename}</h1>
        <p className="mt-1 text-sm text-slate-600">
          <StatusBadge value={upload.status} /> {formatBytes(upload.size_bytes)} · {upload.entry_count} entries ·
          {' '}{templates.length > 0 ? `${templates.length}+ templates` : 'no templates'} · parser: {upload.parser_used ?? 'unknown'} ·
          uploaded {formatDate(upload.created_at)}
        </p>
      </header>

      <div className="rounded-lg border bg-white p-4">
        <h2 className="mb-2 font-medium">Most frequent templates</h2>
        {templates.length === 0 ? (
          <p className="text-sm text-slate-500">No templates available.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {templates.map((t) => (
              <li key={t.template_id}>
                <button
                  type="button"
                  onClick={() => reset(() => setTemplateId(templateId === t.template_id ? undefined : t.template_id))}
                  className={`text-left font-mono hover:underline ${templateId === t.template_id ? 'font-bold text-blue-700' : ''}`}
                >
                  {t.occurrences}× {t.template_text}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex flex-wrap gap-3">
        <input type="search" aria-label="Search messages" placeholder="Search messages" value={q}
          onChange={(e) => reset(() => setQ(e.target.value))} className="rounded-md border px-3 py-1.5 text-sm" />
        <select aria-label="Filter by level" value={level} onChange={(e) => reset(() => setLevel(e.target.value))}
          className="rounded-md border px-3 py-1.5 text-sm">
          <option value="">All levels</option>
          {facets.levels.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
        <select aria-label="Filter by service" value={service} onChange={(e) => reset(() => setService(e.target.value))}
          className="rounded-md border px-3 py-1.5 text-sm">
          <option value="">All services</option>
          {facets.services.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      {error && <ErrorMessage message={error} />}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="overflow-x-auto rounded-lg border bg-white lg:col-span-2">
          {!entries ? <Spinner /> : entries.items.length === 0 ? (
            <p className="p-6 text-center text-slate-500">No entries match these filters.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr><th className="p-2">#</th><th className="p-2">Time</th><th className="p-2">Level</th><th className="p-2">Service</th><th className="p-2">Message</th></tr>
              </thead>
              <tbody>
                {entries.items.map((e) => (
                  <tr key={e.id} onClick={() => setSelected(e)} className="cursor-pointer border-t hover:bg-slate-50">
                    <td className="p-2">{e.line_number}</td>
                    <td className="whitespace-nowrap p-2">{formatDate(e.timestamp)}</td>
                    <td className="p-2"><StatusBadge value={e.level} /></td>
                    <td className="p-2">{e.service}</td>
                    <td className="max-w-md truncate p-2" title={e.message}>{e.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {entries && <div className="px-3"><Pagination page={entries.page} pageSize={entries.page_size} total={entries.total} onChange={setPage} /></div>}
        </div>

        <aside aria-label="Entry details" className="rounded-lg border bg-white p-4 text-sm">
          <h2 className="mb-2 font-medium">Entry details</h2>
          {!selected ? <p className="text-slate-500">Select a row to inspect it.</p> : (
            <dl className="space-y-2">
              <div><dt className="text-slate-500">Source</dt><dd>{selected.source_file} line {selected.line_number}</dd></div>
              <div><dt className="text-slate-500">Host</dt><dd>{selected.hostname}</dd></div>
              <div><dt className="text-slate-500">Template</dt><dd className="font-mono">{selected.template_text ?? 'unknown'}</dd></div>
              <div><dt className="text-slate-500">Parameters</dt><dd className="font-mono">{selected.parameters?.length ? selected.parameters.join(', ') : 'none'}</dd></div>
              <div><dt className="text-slate-500">Original line{selected.truncated ? ' (truncated)' : ''}</dt>
                <dd className="whitespace-pre-wrap break-all font-mono">{selected.original_message}</dd></div>
            </dl>
          )}
        </aside>
      </div>
    </section>
  )
}
