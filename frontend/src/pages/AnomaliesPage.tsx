import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import DataTable from '../components/common/DataTable'
import EmptyState from '../components/common/EmptyState'
import ErrorMessage from '../components/common/ErrorMessage'
import Pagination from '../components/common/Pagination'
import { useToast } from '../components/common/Toast'
import { incidentService } from '../services/incidentService'
import { logService } from '../services/logService'
import type { AnalysisResult, Anomaly } from '../types/incidents'
import type { LogUpload, Page } from '../types/logs'
import { getErrorMessage } from '../utils/errors'
import { formatDate } from '../utils/format'

export default function AnomaliesPage() {
  const { notify } = useToast()
  const [uploads, setUploads] = useState<LogUpload[]>([])
  const [uploadId, setUploadId] = useState<number | undefined>()
  const [windowSeconds, setWindowSeconds] = useState(60)
  const [detectedOnly, setDetectedOnly] = useState(true)
  const [page, setPage] = useState(1)
  const [data, setData] = useState<Page<Anomaly> | null>(null)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    logService.list({ page: 1, status: 'COMPLETED' }).then((p) => {
      setUploads(p.items)
      if (p.items[0]) setUploadId((cur) => cur ?? p.items[0].id)
    }).catch((e) => setError(getErrorMessage(e)))
  }, [])

  useEffect(() => {
    if (uploadId === undefined) return
    incidentService.anomalies({ page, upload_id: uploadId, detected_only: detectedOnly })
      .then((d) => { setData(d); setError(null) }).catch((e) => setError(getErrorMessage(e)))
  }, [uploadId, page, detectedOnly, result])

  const run = async () => {
    if (uploadId === undefined) return
    setRunning(true)
    try {
      const r = await incidentService.analyzeLog(uploadId, windowSeconds)
      setResult(r); setPage(1)
      notify('success', `Analysis finished: ${r.anomalous_windows} anomalous window(s), ${r.incidents_created} new incident(s).`)
    } catch (e) {
      notify('error', getErrorMessage(e))
    } finally {
      setRunning(false)
    }
  }

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-semibold">Anomaly detection</h1>
      {error && <ErrorMessage message={error} />}
      {uploads.length === 0 ? <EmptyState message="Upload and parse a log file first (Logs page)." /> : (
        <div className="flex flex-wrap items-end gap-3 rounded-lg border bg-white p-4">
          <label className="text-sm">Log file
            <select aria-label="Log file" value={uploadId} onChange={(e) => { setUploadId(Number(e.target.value)); setPage(1); setResult(null) }} className="ml-2 rounded border px-2 py-1">
              {uploads.map((u) => <option key={u.id} value={u.id}>{u.filename}</option>)}
            </select>
          </label>
          <label className="text-sm">Window
            <select aria-label="Window size" value={windowSeconds} onChange={(e) => setWindowSeconds(Number(e.target.value))} className="ml-2 rounded border px-2 py-1">
              <option value={60}>1 minute</option><option value={300}>5 minutes</option>
            </select>
          </label>
          <button type="button" disabled={running} onClick={() => void run()} className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white disabled:opacity-60">
            {running ? 'Analyzing…' : 'Run anomaly detection'}
          </button>
        </div>
      )}
      {result && (
        <div className="rounded-lg border bg-white p-4 text-sm">
          <p><strong>{result.anomalous_windows}</strong> of {result.windows_analyzed} windows flagged using <code>{result.method}</code>.
            {result.entries_without_timestamp > 0 && ` ${result.entries_without_timestamp} entries had no timestamp and were skipped.`}</p>
          <p className="mt-1">Incidents created: {result.incidents_created}, updated: {result.incidents_updated}.{' '}
            {result.incident_ids.map((id) => <Link key={id} to={`/incidents/${id}`} className="mr-2 text-blue-600 hover:underline">INC-{1000 + id}</Link>)}</p>
          <p className="mt-1 text-xs text-slate-500">{result.note}</p>
        </div>
      )}
      {data && (
        <>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={detectedOnly} onChange={(e) => { setDetectedOnly(e.target.checked); setPage(1) }} /> Show anomalous windows only</label>
          {data.items.length === 0 ? <EmptyState message="No windows to show. Run anomaly detection or untick the filter." /> : (
            <>
              <DataTable<Anomaly> rowKey={(a) => a.id} rows={data.items} columns={[
                { header: 'Window start', cell: (a) => formatDate(a.window_start) },
                { header: 'Service', cell: (a) => a.affected_service },
                { header: 'Score / threshold', cell: (a) => `${a.anomaly_score} / ${a.threshold}` },
                { header: 'Flagged', cell: (a) => (a.anomaly_detected ? 'Yes' : 'No') },
                { header: 'Method', cell: (a) => a.method },
                { header: 'Top contributing features', cell: (a) => a.contributing_features.map((f) => `${f.name} (${f.z_score})`).join(', ') || 'none' },
              ]} />
              <Pagination page={data.page} pageSize={data.page_size} total={data.total} onChange={setPage} />
              <p className="text-xs text-slate-500">Scores are model-specific and are not probabilities.</p>
            </>
          )}
        </>
      )}
    </section>
  )
}
